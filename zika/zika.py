from __future__ import division, print_function
from collections import defaultdict
import sys
sys.path.append('')  # need to import from base
sys.path.append('/home/richard/Projects')  # need to import from base
from base.io_util import make_dir, remove_dir, tree_to_json, write_json, myopen
from base.sequences import sequence_set, num_date
from base.tree import tree
from base.process import process
from base.frequencies import alignment_frequencies, tree_frequencies
from Bio import SeqIO
from Bio.SeqFeature import FeatureLocation
import numpy as np
from datetime import datetime

region_cmap = [
    ["southeast_asia",     "#462EB9"],
    ["oceania",            "#3F4FCC"],
    ["china",              "#4271CE"],
    ["japan_korea",        "#4B8DC2"],
    ["europe",             "#58A2AC"],
    ["south_america",      "#69B091"],
    ["north_america",      "#E0A33B"]
]

country_cmap = [

    # "#571EA2", "#4B26B1", "#4433BE", "#4042C7", "#3F52CD", "#3F63CF", "#4272CE", "#4580CA", "#4A8CC2", "#5097BA"
    # "#56A0AE", "#5DA8A3", "#66AE96", "#6EB389", "#79B77D", "#83BA70", "#8EBC66", "#9ABE5C", "#A6BE55", "#B2BD4D"
    # "#BDBB48", "#C8B944", "#D1B340", "#D9AD3D", "#DFA43B", "#E49938", "#E68B35", "#E67C32", "#E56A2F", "#E2562B", "#DF4327", "#DC2F24"

    # Old World: "#571EA2", "#4B26B1", "#4433BE", "#4042C7", "#3F52CD", "#3F63CF", "#4272CE", "#4580CA", "#4A8CC2", "#5097BA"
    ["thailand",           "#571EA2"],
    ["singapore",          "#4B26B1"],
    ["french_polynesia",   "#4433BE"],
    ["american_samoa",	   "#4042C7"],
    ["tonga",	           "#3F52CD"],
    ["china",			   "#3F63CF"],
    ["japan",			   "#4272CE"],
    ["italy",			   "#4580CA"],
    # South America: "#56A0AE", "#5DA8A3", "#66AE96", "#6EB389", "#79B77D", "#83BA70", "#8EBC66", "#9ABE5C", "#A6BE55", "#B2BD4D"
    ["brazil",  		   "#56A0AE"],
    ["ecuador",  		   "#5DA8A3"],
    ["colombia",  		   "#66AE96"],
    ["french_guiana",  	   "#6EB389"],
    ["suriname",  		   "#79B77D"],
    ["venezuela",  		   "#83BA70"],
    # Central and North America: "#BDBB48", "#C8B944", "#D1B340", "#D9AD3D", "#DFA43B", "#E49938", "#E68B35", "#E67C32", "#E56A2F",
    # "#E2562B", "#DF4327", "#DC2F24"
    ["panama",             "#BDBB48"],
    ["nicaragua",          "#C8B944"],
    ["honduras",           "#D1B340"],
    ["guatemala",  		   "#D9AD3D"],
    ["mexico",             "#DFA43B"],
    ["martinique",  	   "#E49938"],
    ["guadeloupe",         "#E68B35"],
    ["usvi",               "#E67C32"],
    ["puerto_rico",  	   "#E67732"],
    ["jamaica",            "#E56A2F"],
    ["dominican_republic", "#E2562B"],
    ["haiti",  			   "#DF4327"],
    ["usa",                "#DC2F24"]
]


attribute_nesting = {'geographic location':['region', 'country'], 'authors':['authors']}
geo_attributes = ['region', 'country']
panels = ['tree', 'map', 'entropy']
color_options = {
    "country":{"key":"country", "legendTitle":"Country", "menuItem":"country", "type":"discrete", "color_map": country_cmap},
    "region":{"key":"region", "legendTitle":"Region", "menuItem":"region", "type":"discrete", "color_map": region_cmap},
    "num_date":{"key":"num_date", "legendTitle":"Sampling date", "menuItem":"date", "type":"continuous"},
    "gt":{"key":"genotype", "legendTitle":"Genotype", "menuItem":"genotype", "type":"discrete"}
}

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process virus sequences, build tree, and prepare of web visualization')
    parser.add_argument('-v', '--viruses_per_month', type = int, default = 100, help='number of viruses sampled per month')
    parser.add_argument('-r', '--raxml_time_limit', type = float, default = 1.0, help='number of hours raxml is run')
    parser.add_argument('--verbose', type = int, default = 2, help='throttle treetime output')
    parser.add_argument('--confidence', default = False, action="store_true", help='evaluate confidence intervals of internal node timing')
    parser.add_argument('--load', action='store_true', help = 'recover from file')
    params = parser.parse_args()

    lineage = 'zika'
    input_data_path = '../fauna/data/'+lineage
    store_data_path = 'store/'+lineage + '_'
    build_data_path = 'build/'+lineage + '_'

    zika = process(input_data_path = input_data_path,
                   store_data_path = store_data_path,
                   build_data_path = build_data_path,
                   reference='zika/metadata/zika_outgroup.gb',
                   lat_long_fname='../fauna/source-data/geo_lat_long.tsv',
                   proteins=['CA', 'PRO', 'MP', 'ENV', 'NS1', 'NS2A',
                             'NS2B', 'NS3', 'NS4A', 'NS4B', 'NS5'],
                   method='SLSQP', verbose=params.verbose)
    if params.load:
        zika.load()
    else:
        fasta_fields = {0:'strain', 2:'accession', 3:'date', 4:'region', 5:'country',
                        6:'division', 8:'db', 10:'authors'}
        zika.load_sequences(fields=fasta_fields)
        zika.seqs.filter(lambda s: s.attributes['date']>=datetime(2012,1,1).date() and
                                   s.attributes['date']< datetime(2017,1,1).date())
        zika.seqs.filter(lambda s: len(s.seq)>=2000)
        dropped_strains = [
            "THA/PLCal_ZV/2013", "PLCal_ZV", # true strains, too basal for analysis
            "ZF36_36S", # possible contamination
            "Dominican_Republic/2016/PD2", "GD01", "GDZ16001", "VEN/UF_2/2016", # true strains, but duplicates of other strains in dataset
            "Bahia04" # excessive terminal branch length
        ]
        zika.seqs.filter(lambda s: s.id not in dropped_strains)
        zika.seqs.subsample(category = lambda x:(x.attributes['date'].year, x.attributes['date'].month),
            threshold=params.viruses_per_month)

        zika.align()
        zika.build_tree()
        zika.dump()
    zika.clock_filter(n_iqd=3, plot=True)
    zika.annotate_tree(Tc=0.02, timetree=True, reroot='best', confidence=params.confidence)
    for geo_attr in geo_attributes:
        zika.tree.geo_inference(geo_attr)
    zika.export(controls = attribute_nesting, geo_attributes = geo_attributes,
                color_options=color_options, panels=panels)

    plot_skyline = False
    if plot_skyline: # plot an approximate skyline
        from matplotlib import pyplot as plt
        T = zika.tree.tt
        plt.figure()
        skyline = T.merger_model.skyline(n_points = 20, gen = 50/T.date2dist.slope,
                                         to_numdate = T.date2dist.to_numdate)
        plt.ticklabel_format(useOffset=False)
        plt.plot(skyline.x, skyline.y)
        plt.ylabel('effective population size')
        plt.xlabel('year')
        plt.savefig('zika_skyline.png')
