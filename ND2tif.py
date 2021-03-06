import os
import time
import logging
import argparse
from tqdm import tqdm
from multiprocessing.pool import Pool
from nd2reader import ND2Reader
from skimage.external import tifffile 
from ND2tif_utils import *

def ParseMultiPointND2(pid, in_path, out_path, start, end, channels=None, zproject=None, size=None, itpl=3, to_dtype='uint8',
                       wishdict={}):

    with ND2Reader(in_path) as images:
        images.bundle_axes = 'zcyx'
        images.iter_axes = 'v'

        # compile additional metadata:     
        res = 1/images.metadata['pixel_microns']
        addMeta = get_addmeta(images, wishdict)

        # process series:
        try:
            for v, im in enumerate(tqdm(images[start:end], total = len(images[start:end]), unit='files', postfix=pid)):
                
                # optional channel selection/re-ordering
                if channels: 
                    im = selectch(im, channels)
                
                # optional zproject
                if zproject:
                    im = projectz(im, zproject)

                # optional resize
                if size:
                    im = resize(im, size, itpl)
                    
                # potential dtype conversion
                if to_dtype != str(im.dtype):
                    im = dtype_conversion(im, to_dtype, forcecopy=False)

                # saving
                fpath = f"{out_path}_{str(start + v)}.tiff"
                savetiff(im, fpath, res, addMeta)
        except: logging.exception('Exception occured: ')

if __name__ == '__main__':

    # parameters:
    parser = argparse.ArgumentParser()

    class handledict(argparse.Action):
        def __call__(self, parser, namespace, instring, option_string=None):
            my_dict = {}
            for keyval in instring.split(","):
                print(keyval)
                key,val = keyval.split(":")
                my_dict[key] = val
            setattr(namespace, self.dest, my_dict)

    parser.add_argument('indir', type=str, help='Specify path to input directory')
    parser.add_argument('outdir', type=str, help='Specify path output directory')
    parser.add_argument('-c', '--channels', type=int, nargs='*', default=None, help='provide list to specify channels to be extracted and/or reorder them, e.g. [1,2,0,3]')
    parser.add_argument('-z', '--zproject', type=str, default=None, help='provide string to specify mode of z-projection, e.g. max_project') #TODO: add options
    parser.add_argument('-s', '--size', type=int, nargs='*', default=None, help='provide tuple of target dimensions for output images, e.g. (512,512)')
    parser.add_argument('-i', '--itpl', type=int, default=3, help='provide int [0-5] to specify mode of interpolation to be used in resize (default: 3 -> bicubic)')
    parser.add_argument('-d', '--dtype', type=str, default='uint8', help='provide string specifying the desired dtype of output images (default: uint8)')
    parser.add_argument('-wd', '--wishdict', default={}, action=handledict, help='provide key1:value1,key2:value2,... to try to extract metadata items from the image according to values.')
    parser.add_argument('-t', '--tag', type=str, default=None, help='specify additional string to be added to output filenames (default: None)')
    parser.add_argument('-r', '--range', type=int, nargs='*', default=None, help='provide list [L1,L2] to limit which multipoints to process (default: None)')
    parser.add_argument('-w', '--workers', type=int, default=1, help='specify number of workers (default: 1)')
    params = parser.parse_args()

    flist = [params.indir + f for f in os.listdir(params.indir) if f.split('.')[-1] == 'nd2']
    for ND2file in flist:
        t00 = time.time()
        # setup list_len and naming:
        with ND2Reader(ND2file) as images:
            images.bundle_axes = 'zcyx'
            images.iter_axes = 'v'
            list_len = len(images)
            if params.range: 
                L1, L2 = params.range
                assert L1 < list_len and L2 <= list_len, f'Range out of bounds. Only {list_len} images in {ND2file}'
                list_len = L2 - L1
            else: L1 = 0
                
            # TODO: make this call a function:
            fn = images.filename.split('/')[-1]
            assert len(fn.split('_')) == 3, \
            'Please name your files according to: [yyyy-m-d_Plate-de-script-tion_Idx.nd2]'
            fn = '_'.join(fn.split('_')[1:3]).split('.')[0]
            if params.tag: fn = f"{fn}_{params.tag}"
            out_path = params.outdir + fn
            
        
        # Multiprocess setup. 
        # Will never use more cores than images to be extracted.
        process_num = np.min([params.workers, list_len])

        print('-------------------')
        print(f"Starting image extraction for: {ND2file}")
        print(f"Total images to be extracted {list_len}")
        print(f"Workers: {process_num}")
        print('Parent process %s.' % os.getpid())
        print(f"Output directory: {out_path}")
        print('-------------------')
        p = Pool(process_num)
        for i in range(process_num):
            start = int(L1 + (i * list_len / process_num))
            end = int(L1 + ((i + 1) * list_len / process_num))
            p.apply_async(
                ParseMultiPointND2, args=(str(i), ND2file, out_path, start, end,
                params.channels, 
                params.zproject, 
                tuple(params.size),
                params.itpl,
                params.dtype,
                params.wishdict
                )
            )

        print('Waiting for all subprocesses done...')
        p.close()
        p.join()
        print('All subprocesses done.')
        print(f"Total execution time: {time.time() - t00}")
        print(f"Time-per-image: {(time.time() - t00)/list_len}")

