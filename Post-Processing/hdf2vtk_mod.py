"""hdf2vtk: convert Dedalus fields stored in HDF5 files to vtk format for 3D visualization

Usage:
    hdf2vtk [--fields=<fields> --fluctfields=<ffields> --series=<True/False> --nt=<nt> --] <input_file> [<output_file>]

Options:
    --fields=<fields>           comma separated list of fields to extract from the hdf5 file [default: None]
    --nt=<nt>                   time index [default: -1]
    --series=<True/False>       If True, the input file is the directory containing the snapshots. The code generates
                                numbered vtr files, one for each time saved. If False it generates only one file from input files
    --fluctfields=<ffields>     comma separated list of fields for which a fluctuation field is created based
                                on the snapshot's xy spatial averaged profile. The instantaneous variable must be in <fields>

"""
from dedalus.extras import plot_tools
from pathlib import Path
from docopt import docopt
from pyevtk.hl import gridToVTK
import h5py
import numpy as np
import json
import natsort
H5_FIELD_PATH = 'tasks/'
H5_SCALE_PATH = 'scales/'
H5_DIM_LABEL = 'DIMENSION_LABELS'
H5_STR_DECODE = 'UTF-8'

if __name__ == "__main__":
    args = docopt(__doc__ )

    nt = int(args['--nt'])
    if args['--series'] == 'True':
        fseries = True
    else:
        fseries = False

    fields = args['--fields']
    if fields is None:
        raise ValueError("Must specify fields to copy.")
    fields = fields.split(',')
    print("fields = {}".format(fields))

    ffields = args['--fluctfields']
    if ffields is None:
        ffields = [] # raise ValueError("Must specify fields to copy.")
    ffields = ffields.split(',')
    print("ffields = {}".format(ffields))

    infile = Path(args['<input_file>'])
    if fseries:
        p = Path(args['<input_file>']+'/')
        lh5 = list(p.glob('*h5'))
        lh5 = natsort.natsorted(lh5)
    else:
        lh5 = [infile]

    if args['<output_file>']:
        outfile = args['<output_file>']
    else:
        outfile = infile.stem
    if fseries:
        dseries = dict()
        dseries["file-series-version"] = "1.0"
        ldsnap = []

    print("outfile = {}".format(outfile))
    ncount = 0
    for fname in lh5:
        datafile = h5py.File(fname,"r")
        print('Time = ',datafile['scales/sim_time'][:])
        if fseries:
            for nt in range(datafile['scales/sim_time'].shape[0]):
                tsnap = datafile['scales/sim_time'][nt]
                field_names = [H5_FIELD_PATH+f for f in fields]
                dim_labels = datafile[field_names[0]].attrs[H5_DIM_LABEL][1:]
                if len(dim_labels) != 3:
                    raise NotImplementedError("hdf2vtk only supports 3D data.")

                # currently cartesian only
                scale_names = [H5_SCALE_PATH+d for d in dim_labels]
                # just get first scale you find...
                grid_scale = list(datafile[scale_names[0]].keys())[0]
                scale_names = [sn+'/'+grid_scale for sn in scale_names]
                x = plot_tools.get_1d_vertices(datafile[scale_names[0]][:])
                y = plot_tools.get_1d_vertices(datafile[scale_names[1]][:])
                z = plot_tools.get_1d_vertices(datafile[scale_names[2]][:])

                cellData = {}
                for i, f in enumerate(fields):
                    # print(i,f)
                    #cellData[f] = np.asfortranarray(datafile[field_names[i]][nt])
                    cellData[f] = datafile[field_names[i]][nt]
                    if f in ffields:
                        print(f,f+'p')
                        ainst = np.copy(datafile[field_names[i]][nt])
                        ap = np.zeros_like(ainst)
                        amean = np.mean(ainst,axis=(0,1))
                        for k in range(ainst.shape[2]):
                            ap[:,:,k] = ainst[:,:,k] - amean[k]
                        cellData[f+'p'] = ap

                fnameout = outfile+"_"+str(ncount).zfill(4)
                gridToVTK(fnameout, x, y, z, cellData = cellData)
                dsnap = dict()
                dsnap["name"] = fnameout+".vtr"
                dsnap["time"] = tsnap
                ldsnap.append(dsnap)
                ncount += 1
            else:
                tsnap = datafile['scales/sim_time'][nt]
                field_names = [H5_FIELD_PATH+f for f in fields]
                dim_labels = datafile[field_names[0]].attrs[H5_DIM_LABEL][1:]
                if len(dim_labels) != 3:
                    raise NotImplementedError("hdf2vtk only supports 3D data.")

                # currently cartesian only
                scale_names = [H5_SCALE_PATH+d for d in dim_labels]
                # just get first scale you find...
                grid_scale = list(datafile[scale_names[0]].keys())[0]
                scale_names = [sn+'/'+grid_scale for sn in scale_names]
                x = plot_tools.get_1d_vertices(datafile[scale_names[0]][:])
                y = plot_tools.get_1d_vertices(datafile[scale_names[1]][:])
                z = plot_tools.get_1d_vertices(datafile[scale_names[2]][:])

                cellData = {}
                for i, f in enumerate(fields):
                    # print(i,f)
                    #cellData[f] = np.asfortranarray(datafile[field_names[i]][nt])
                    cellData[f] = datafile[field_names[i]][nt]
                    if f in ffields:
                        print(f,f+'p')
                        ainst = np.copy(datafile[field_names[i]][nt])
                        ap = np.zeros_like(ainst)
                        amean = np.mean(ainst,axis=(0,1))
                        for k in range(ainst.shape[2]):
                            ap[:,:,k] = ainst[:,:,k] - amean[k]
                        cellData[f+'p'] = ap
                gridToVTK(outfile, x, y, z, cellData = cellData)
if fseries:
    dseries["files"] = ldsnap
    with open(outfile+".vtr.series","w",encoding='utf-8') as write_file:
        json.dump(dseries,write_file,ensure_ascii=False,indent=4)
