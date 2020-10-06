__author__ = 'mhgou'
__version__ = '1.0'

import numpy as np
import open3d as o3d
import copy
import cv2
from .utils.utils import plot_gripper_pro_max, batch_rgbdxyz_2_rgbxy_depth, get_batch_key_points, batch_key_points_2_tuple
GRASP_ARRAY_LEN = 17
RECT_GRASP_ARRAY_LEN = 7

class Grasp():
    def __init__(self, *args):
        '''
        **Input:**

        - args can be a numpy array or tuple of the score, width, height, depth, rotation_matrix, translation, object_id

        - the format of numpy array is [score, width, height, depth, rotation_matrix(9), translation(3), object_id]

        - the length of the numpy array is 17.
        '''
        if len(args) == 1:
            if type(args[0]) == np.ndarray:
                self.grasp_array = copy.deepcopy(args[0])
            else:
                raise TypeError('if only one arg is given, it must be np.ndarray.')
        elif len(args) == 7:
            score, width, height, depth, rotation_matrix, translation, object_id = args
            self.grasp_array = np.concatenate([np.array((score, width, height, depth)),rotation_matrix.reshape(-1), translation, np.array((object_id))]).astype(np.float32)
        else:
            raise ValueError('only 1 or 7 arguments are accepted')
    
    def __repr__(self):
        return 'Grasp: score:{}, width:{}, height:{}, depth:{}, translation:{}\nrotation:\n{}\nobject id:{}'.format(self.score(), self.width(), self.height(), self.depth(), self.translation(), self.rotation_matrix(), self.object_id())

    def score(self):
        '''
        **Output:**

        - float of the score.
        '''
        return float(self.grasp_array[0])

    def width(self):
        '''
        **Output:**

        - float of the width.
        '''
        return float(self.grasp_array[1])
    
    def height(self):
        '''
        **Output:**

        - float of the height.
        '''
        return float(self.grasp_array[2])

    def depth(self):
        '''
        **Output:**

        - float of the depth.
        '''
        return float(self.grasp_array[3])

    def rotation_matrix(self):
        '''
        **Output:**

        - np.array of shape (3, 3) of the rotation matrix.
        '''
        return self.grasp_array[4:13].reshape((3,3))

    def translation(self):
        '''
        **Output:**

        - np.array of shape (3,) of the translation.
        '''
        return self.grasp_array[13:16]

    def object_id(self):
        '''
        **Output:**

        - int of the object id that this grasp grasps
        '''
        return int(self.grasp_array[16])

    def to_open3d_geometry(self):
        '''
        **Ouput:**

        - list of open3d.geometry.Geometry of the gripper.
        '''
        return plot_gripper_pro_max(self.translation(), self.rotation_matrix(), self.width(), self.depth(), score = self.score())

class GraspGroup():
    def __init__(self, *args):
        '''
        **Input:**

        - args can be (1) nothing (2) list of Grasp instances.
        '''
        if len(args) == 0:
            self.grasp_group_array = np.zeros((0, GRASP_ARRAY_LEN), dtype=np.float32)
        elif len(args) == 1:
            grasp_list = args
            self.grasp_group_array = np.zeros((0, GRASP_ARRAY_LEN), dtype=np.float32)
            for grasp in grasp_list:
                self.grasp_group_array = np.concatenate((self.grasp_group_array, grasp.grasp_array.reshape((-1, GRASP_ARRAY_LEN))))
        else:
            raise ValueError('args must be nothing or list of Grasp instances.')

    def __len__(self):
        '''
        **Output:**

        - int of the length.
        '''
        return len(self.grasp_group_array)

    def __repr__(self):
        repr = '----------\nGrasp Group, Number={}:\n'.format(self.__len__())
        if self.__len__() <= 6:
            for grasp_array in self.grasp_group_array:
                repr += Grasp(grasp_array).__repr__() + '\n'
        else:
            for i in range(3):
                repr += Grasp(self.grasp_group_array[i]).__repr__() + '\n'
            repr += '......\n'
            for i in range(3):
                repr += Grasp(self.grasp_group_array[-(3-i)]).__repr__() + '\n'
        return repr + '----------'

    def __getitem__(self, index):
        '''
        **Input:**

        - index: int or slice.

        **Output:**

        - if index is int, return Grasp instance.

        - if index is slice, return GraspGroup instance.
        '''
        if type(index) == int:
            return Grasp(self.grasp_group_array[index])
        elif type(index) == slice:
            graspgroup = GraspGroup()
            graspgroup.grasp_group_array = copy.deepcopy(self.grasp_group_array[index])
            return graspgroup
        else:
            raise TypeError('unknown type "{}" for calling __getitem__ for GraspGroup'.format(type(index)))

    def scores(self):
        '''
        **Output:**

        - numpy array of shape (-1, ) of the scores.
        '''
        return self.grasp_group_array[:,0]

    def widths(self):
        '''
        **Output:**

        - numpy array of shape (-1, ) of the widths.
        '''
        return self.grasp_group_array[:,1]
    
    def heights(self):
        '''
        **Output:**

        - numpy array of shape (-1, ) of the heights.
        '''
        return self.grasp_group_array[:,2]

    def depths(self):
        '''
        **Output:**

        - numpy array of shape (-1, ) of the depths.
        '''
        return self.grasp_group_array[:,3]

    def rotation_matrices(self):
        '''
        **Output:**

        - np.array of shape (-1, 3, 3) of the rotation matrices.
        '''
        return self.grasp_group_array[:, 4:13].reshape((-1, 3, 3))

    def translations(self):
        '''
        **Output:**

        - np.array of shape (-1, 3) of the translations.
        '''
        return self.grasp_group_array[:, 13:16]

    def object_ids(self):
        '''
        **Output:**

        - numpy array of shape (-1, ) of the object ids.
        '''
        return self.grasp_group_array[:,16].astype(np.int32)

    def add(self, grasp):
        '''
        **Input:**

        - grasp: Grasp instance
        '''
        self.grasp_group_array = np.concatenate((self.grasp_group_array, grasp.grasp_array.reshape((-1, GRASP_ARRAY_LEN))))

    def remove(self, index):
        '''
        **Input:**

        - index: list of the index of grasp
        '''
        self.grasp_group_array = np.delete(self.grasp_group_array, index, axis = 0)

    def from_npy(self, npy_file_path):
        '''
        **Input:**

        - npy_file_path: string of the file path.
        '''
        self.grasp_group_array = np.load(npy_file_path)

    def save_npy(self, npy_file_path):
        '''
        **Input:**

        - npy_file_path: string of the file path.
        '''
        np.save(npy_file_path, self.grasp_group_array)

    def to_open3d_geometry_list(self):
        '''
        **Output:**

        - list of open3d.geometry.Geometry of the grippers.
        '''
        geometry = []
        for i in range(len(self.grasp_group_array)):
            g = Grasp(self.grasp_group_array[i])
            geometry.append(g.to_open3d_geometry())
        return geometry
    
    def sort_by_score(self, reverse = False):
        '''
        **Input:**

        - reverse: bool of order, if True, from high to low, if False, from low to high.

        **Output:**

        - no output but sort the grasp group.
        '''
        score = self.grasp_group_array[:,0]
        index = np.argsort(score)
        if not reverse:
            index = index[::-1]
        self.grasp_group_array = self.grasp_group_array[index]

    def random_sample(self, numGrasp = 20):
        '''
        **Input:**

        - numGrasp: int of the number of sampled grasps.

        **Output:**

        - GraspGroup instance of sample grasps.
        '''
        if numGrasp > self.__len__():
            raise ValueError('Number of sampled grasp should be no more than the total number of grasps in the group')
        shuffled_grasp_group_array = copy.deepcopy(self.grasp_group_array)
        np.random.shuffle(shuffled_grasp_group_array)
        shuffled_grasp_group = GraspGroup()
        shuffled_grasp_group.grasp_group_array = copy.deepcopy(shuffled_grasp_group_array[:numGrasp])
        return shuffled_grasp_group

    def to_rect_grasp_group(self, camera):
        '''
        **Input:**

        - camera: string of type of camera, 'realsense' or 'kinect'.

        **Output:**
        
        - RectGraspGroup instance.
        '''
        tranlations = self.translations()
        rotations = self.rotation_matrices()
        depths = self.depths()
        scores = self.scores()
        widths = self.widths()
        object_ids = self.object_ids()

        mask = (rotations[:, 2, 0] > 0.99)
        tranlations = tranlations[mask]
        depths = depths[mask]
        widths = widths[mask]
        scores = scores[mask]
        rotations = rotations[mask]
        object_ids = object_ids[mask]

        k_points = get_batch_key_points(tranlations, rotations, widths)
        k_points = k_points.reshape([-1, 3])
        k_points = k_points.reshape([-1, 4, 3])
        rect_grasp_group_array = batch_key_points_2_tuple(k_points, scores, object_ids, camera)
        rect_grasp_group = RectGraspGroup()
        rect_grasp_group.rect_grasp_group_array = rect_grasp_group_array
        return rect_grasp_group

class RectGrasp():
    def __init__(self, *args):
        '''
        **Input:**

        - args can be a numpy array or tuple of the center_x, center_y, open_x, open_y, height, score, object_id

        - the format of numpy array is [center_x, center_y, open_x, open_y, height, score, object_id]

        - the length of the numpy array is 7.
        '''
        if len(args) == 1:
            if type(args[0]) == np.ndarray:
                self.rect_grasp_array = copy.deepcopy(args[0])
            else:
                raise TypeError('if only one arg is given, it must be np.ndarray.')
        elif len(args) == RECT_GRASP_ARRAY_LEN:
            self.rect_grasp_array = np.array(args).astype(np.float32)
        else:
            raise ValueError('only one or six arguments are accepted')
    
    def __repr__(self):
        return 'Rectangle Grasp: score:{}, height:{}, open point:{}, center point:{}, object id:{}'.format(self.score(), self.height(), self.open_point(), self.center_point(), self.object_id())

    def score(self):
        '''
        **Output:**

        - float of the score.
        '''
        return self.rect_grasp_array[5]

    def height(self):
        '''
        **Output:**

        - float of the height.
        '''
        return self.rect_grasp_array[4]
    
    def open_point(self):
        '''
        **Output:**

        - tuple of x,y of the open point.
        '''
        return (self.rect_grasp_array[2], self.rect_grasp_array[3])

    def center_point(self):
        '''
        **Output:**

        - tuple of x,y of the center point.
        '''
        return (self.rect_grasp_array[0], self.rect_grasp_array[1])

    def object_id(self):
        '''
        **Output:**

        - int of the object id that this grasp grasps
        '''
        return int(self.rect_grasp_array[6])

    def to_opencv_image(self, opencv_rgb):
        '''
        **input:**
        
        - opencv_rgb: numpy array of opencv BGR format.

        **Output:**

        - numpy array of opencv RGB format that shows the rectangle grasp.
        '''
        center_x, center_y, open_x, open_y, height, score, object_id = self.rect_grasp_array
        center = np.array([center_x, center_y])
        left = np.array([open_x, open_y])
        axis = left - center
        normal = np.array([-axis[1], axis[0]])
        normal = normal / np.linalg.norm(normal) * height / 2
        p1 = center + normal + axis
        p2 = center + normal - axis
        p3 = center - normal - axis
        p4 = center - normal + axis
        cv2.line(opencv_rgb, (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), (0,0,255), 1, 8)
        cv2.line(opencv_rgb, (int(p2[0]),int(p2[1])), (int(p3[0]),int(p3[1])), (255,0,0), 3, 8)
        cv2.line(opencv_rgb, (int(p3[0]),int(p3[1])), (int(p4[0]),int(p4[1])), (0,0,255), 1, 8)
        cv2.line(opencv_rgb, (int(p4[0]),int(p4[1])), (int(p1[0]),int(p1[1])), (255,0,0), 3, 8)
        return opencv_rgb
        
    def to_grasp(self, camera_intrinsics, depths, depth_method):
        pass
    
class RectGraspGroup():
    def __init__(self, *args):
        '''
        **Input:**

        - args can be (1) nothing (2) list of RectGrasp instances.
        '''
        if len(args) == 0:
            self.rect_grasp_group_array = np.zeros((0, RECT_GRASP_ARRAY_LEN), dtype=np.float32)
        elif len(args) == 1:
            rect_grasp_list = args
            self.rect_grasp_group_array = np.zeros((0, RECT_GRASP_ARRAY_LEN), dtype=np.float32)
            for rect_grasp in rect_grasp_list:
                self.rect_grasp_group_array = np.concatenate((self.rect_grasp_group_array, rect_grasp.reshape((-1, RECT_GRASP_ARRAY_LEN))))
        else:
            raise ValueError('args must be nothing or list of RectGrasp instances.')

    def __len__(self):
        '''
        **Output:**

        - int of the length.
        '''
        return len(self.rect_grasp_group_array)
    
    def __repr__(self):
        repr = '----------\nRectangle Grasp Group, Number={}:\n'.format(self.__len__())
        if self.__len__() <= 10:
            for rect_grasp_array in self.rect_grasp_group_array:
                repr += RectGrasp(rect_grasp_array).__repr__() + '\n'
        else:
            for i in range(5):
                repr += RectGrasp(self.rect_grasp_group_array[i]).__repr__() + '\n'
            repr += '......\n'
            for i in range(5):
                repr += RectGrasp(self.rect_grasp_group_array[-(5-i)]).__repr__() + '\n'
        return repr + '----------'
            
    def __getitem__(self, index):
        '''
        **Input:**

        - index: int or slice.

        **Output:**

        - if index is int, return RectGrasp instance.

        - if index is slice, return RectGraspGroup instance.
        '''
        if type(index) == int:
            return RectGrasp(self.rect_grasp_group_array[index])
        elif type(index) == slice:
            rectgraspgroup = RectGraspGroup()
            rectgraspgroup.rect_grasp_group_array = copy.deepcopy(self.rect_grasp_group_array[index])
            return rectgraspgroup
        else:
            raise TypeError('unknown type "{}" for calling __getitem__ for RectGraspGroup'.format(type(index)))

    def add(self, rect_grasp):
        '''
        **Input:**

        - rect_grasp: RectGrasp instance
        '''
        self.rect_grasp_group_array = np.concatenate((self.rect_grasp_group_array, rect_grasp.rect_grasp_array.reshape((-1, RECT_GRASP_ARRAY_LEN))))

    def remove(self, index):
        '''
        **Input:**

        - index: list of the index of rect_grasp
        '''
        self.rect_grasp_group_array = np.delete(self.rect_grasp_group_array, index, axis = 0)

    def from_npy(self, npy_file_path):
        '''
        **Input:**

        - npy_file_path: string of the file path.
        '''
        self.rect_grasp_group_array = np.load(npy_file_path)

    def save_npy(self, npy_file_path):
        '''
        **Input:**

        - npy_file_path: string of the file path.
        '''
        np.save(npy_file_path, self.rect_grasp_group_array)

    def to_opencv_image(self, opencv_rgb, numGrasp = 0):
        '''
        **input:**
        
        - opencv_rgb: numpy array of opencv BGR format.

        - numGrasp: int of the number of grasp, 0 for all.

        **Output:**

        - numpy array of opencv RGB format that shows the rectangle grasps.
        '''
        img = copy.deepcopy(opencv_rgb)
        if numGrasp == 0:
            numGrasp = self.__len__()
        shuffled_rect_grasp_group_array = copy.deepcopy(self.rect_grasp_group_array)
        np.random.shuffle(shuffled_rect_grasp_group_array)
        for rect_grasp_array in shuffled_rect_grasp_group_array[:numGrasp]:
            center_x, center_y, open_x, open_y, height, score, object_id = rect_grasp_array
            center = np.array([center_x, center_y])
            left = np.array([open_x, open_y])
            axis = left - center
            normal = np.array([-axis[1], axis[0]])
            normal = normal / np.linalg.norm(normal) * height / 2
            p1 = center + normal + axis
            p2 = center + normal - axis
            p3 = center - normal - axis
            p4 = center - normal + axis
            cv2.line(img, (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), (0,0,255), 1, 8)
            cv2.line(img, (int(p2[0]),int(p2[1])), (int(p3[0]),int(p3[1])), (255,0,0), 3, 8)
            cv2.line(img, (int(p3[0]),int(p3[1])), (int(p4[0]),int(p4[1])), (0,0,255), 1, 8)
            cv2.line(img, (int(p4[0]),int(p4[1])), (int(p1[0]),int(p1[1])), (255,0,0), 3, 8)
        return img

    def to_grasp_group(self, camera_intrinsics, depths, depth_method):
        pass

    def sort_by_score(self, reverse = False):
        '''
        **Input:**

        - reverse: bool of order, if True, from high to low, if False, from low to high.

        **Output:**

        - no output but sort the grasp group.
        '''
        score = self.rect_grasp_group_array[:,5]
        index = np.argsort(score)
        if not reverse:
            index = index[::-1]
        self.rect_grasp_group_array = self.rect_grasp_group_array[index]

    def random_sample(self, numGrasp = 20):
        '''
        **Input:**

        - numGrasp: int of the number of sampled grasps.

        **Output:**

        - RectGraspGroup instance of sample grasps.
        '''
        if numGrasp > self.__len__():
            raise ValueError('Number of sampled grasp should be no more than the total number of grasps in the group')
        shuffled_rect_grasp_group_array = copy.deepcopy(self.rect_grasp_group_array)
        np.random.shuffle(shuffled_rect_grasp_group_array)
        shuffled_rect_grasp_group = RectGraspGroup()
        shuffled_rect_grasp_group.rect_grasp_group_array = copy.deepcopy(shuffled_rect_grasp_group_array[:numGrasp])
        return shuffled_rect_grasp_group