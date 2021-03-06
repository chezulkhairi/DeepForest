#!/usr/bin/env python

"""
Copyright 2017-2018 Fizyr (https://fizyr.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import os
import sys
import cv2
import numpy as np

from keras_retinanet.utils.transform import random_transform_generator
from keras_retinanet.utils.visualization import draw_annotations, draw_boxes
from keras_retinanet.preprocessing import onthefly
from keras_retinanet.utils.anchors import anchors_for_shape

def create_generator(args,config):
    """ Create generators for evaluation.
    """
    if  args.dataset_type == 'onthefly':
            
        #Replace config subsample with validation subsample. Not the best, or the worst, way to do this.
        config["subsample"]=config["validation_subsample"]
    
        validation_generator=onthefly.OnTheFlyGenerator(
                    args.annotations,
                batch_size=args.batch_size,
                base_dir=config["evaluation_tile_dir"],
                config=config,
                group_method="none",
                shuffle_groups=False,
                shuffle_tiles=config["shuffle_eval"])   
    else:
        raise ValueError('Invalid data type received: {}'.format(args.dataset_type))

    return validation_generator


def parse_args(args):
    """ Parse the arguments.
    """
    parser     = argparse.ArgumentParser(description='Debug script for a RetinaNet network.')
    subparsers = parser.add_subparsers(help='Arguments for specific dataset types.', dest='dataset_type')
    subparsers.required = True

    def csv_list(string):
        return string.split(',')

    #On the fly parser
    otf_parser = subparsers.add_parser('onthefly')
    otf_parser.add_argument('annotations', help='Path to CSV file containing annotations for training.')

    parser.add_argument('-l', '--loop', help='Loop forever, even if the dataset is exhausted.', action='store_true')
    parser.add_argument('--batch-size',      help='Size of the batches.', default=1, type=int)    
    parser.add_argument('--no-resize', help='Disable image resizing.', dest='resize', action='store_false')
    parser.add_argument('--anchors', help='Show positive anchors on the image.', action='store_true')
    parser.add_argument('--annotations', help='Show annotations on the image. Green annotations have anchors, red annotations don\'t and therefore don\'t contribute to training.', action='store_true')
    parser.add_argument('--random-transform', help='Randomly transform image and annotations.', action='store_true')
    parser.add_argument('--image-min-side', help='Rescale the image so the smallest side is min_side.', type=int, default=800)
    parser.add_argument('--image-max-side', help='Rescale the image if the largest side is larger than max_side.', type=int, default=1333)

    return parser.parse_args(args)


def run(generator, args):
    """ Main loop.

    Args
        generator: The generator to debug.
        args: parseargs args object.
    """
    # display images, one at a time
    for i in range(generator.size()):
        # load the data
        image       = generator.load_image(i)
        annotations = generator.load_annotations(i)

        # apply random transformations
        if args.random_transform:
            image, annotations = generator.random_transform_group_entry(image, annotations)

        # resize the image and annotations
        if args.resize:
            image, image_scale = generator.resize_image(image)
            annotations[:, :4] *= image_scale

        anchors = anchors_for_shape(image.shape)

        labels_batch, regression_batch, boxes_batch = generator.compute_anchor_targets(anchors, [image], [annotations], generator.num_classes())
        anchor_states                               = labels_batch[0, :, -1]

        # draw anchors on the image
        if args.anchors:
            draw_boxes(image, anchors[anchor_states == 1], (255, 255, 0), thickness=1)

        # draw annotations on the image
        if args.annotations:
            # draw annotations in red
            draw_annotations(image, annotations, color=(0, 0, 255), label_to_name=generator.label_to_name)

            # draw regressed anchors in green to override most red annotations
            # result is that annotations without anchors are red, with anchors are green
            draw_boxes(image, boxes_batch[0, anchor_states == 1, :], (0, 255, 0))

        cv2.imshow('Image', image)
        if cv2.waitKey() == ord('q'):
            return False
    return True


def main(config,args=None):
    # parse arguments
    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    # create the generator
    generator = create_generator(args,config)

    # create the display window
    cv2.namedWindow('Image', cv2.WINDOW_NORMAL)

    if args.loop:
        while run(generator, args):
            pass
    else:
        run(generator, args)


if __name__ == '__main__':
    
    
    import numpy as np
    
    np.random.seed(2)
    from DeepForest.config import config    
    from DeepForest import preprocess
    
    
    #Prepare Evaluation
    evaluation=preprocess.load_data(data_dir=config['evaluation_csvs'])
    
    ##Preprocess Filters##
    if config['preprocess']['zero_area']:
        evaluation=preprocess.zero_area(evaluation)
        
    #Write training and evaluation data to file for annotations
    evaluation.to_csv("data/training/evaluation.csv") 
    
    main(config=config)
    
