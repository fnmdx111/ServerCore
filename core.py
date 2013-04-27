# encoding: utf-8
from itertools import product, combinations
import logging
import os
import uuid
from sqlalchemy import Column, String, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np


Base = declarative_base()


class JPEGFileEntry(Base):
    __tablename__ = 'entries'

    id = Column(String, primary_key=True)
    feature_vector = Column(LargeBinary)
    filename = Column(String)

    def __init__(self, filename, feature_vector):
        self.feature_vector = feature_vector
        self.filename = filename


    def __repr__(self):
        return '<JPEGFileEntry %s>' % self.id



class ServerCore(object):
    DCT_CONTAINER_TYPE = np.int64
    GRAYSCALE_CONTAINER_TYPE = np.int16

    def __init__(self, db_path='db.sqlite',
                       (size_h, size_w)=(480, 640)):
        self.db_path = db_path

        self.engine = create_engine('sqlite:///%s' % self.db_path)
        self.session = sessionmaker(bind=self.engine)()

        self.size_h = size_h
        self.size_w = size_w
        self.size_b_h = size_h / 8
        self.size_b_w = size_w / 8

        block_row_idx, block_col_idx = map(lambda end: range(0, end, 8), (size_h, size_w))
        self.block_coordinates = tuple(product(block_row_idx, block_col_idx))

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)


    def add_entry(self, uuid, feature_vector):
        entry = JPEGFileEntry(uuid, feature_vector)
        self.session.add(entry)


    def _dct_img(self, img):
        ret = np.ndarray((self.size_b_h, self.size_b_w),
                         dtype=np.dtype((ServerCore.DCT_CONTAINER_TYPE,
                                         (8, 8))))
        mat = np.zeros((8, 8), dtype=np.float64)
        for r, c in self.block_coordinates:
            mat[:8, :8] = img[r:r + 8, c:c + 8]
            ret[r / 8, c / 8][:, :] = cv2.dct(mat)

        return ret


    def _extract_feat_vec(self, img, n=128):
        return np.array(sorted(map(lambda dct: dct[0, 0], img),
                               reverse=True)[:n if n else None])


    def add_jpeg_file(self, img):
        """@param img:numpy.ndarray: grayscale matrix"""
        dct_img = self._dct_img(img)
        feature_vector = self._extract_feat_vec(self._dct_img(img))

        filename = '%s.jpg' % uuid.uuid1().get_hex()
        self.add_entry(filename, feature_vector.dumps())
        cv2.imwrite('images/%s' % filename, img)


    def retrieve(self, img, n=10):
        """@param img:numpy.ndarray: grayscale matrix"""
        r_fv = self._extract_feat_vec(self._dct_img(img))
        features = []
        query = self.session.query(JPEGFileEntry)
        for entry in self.session.connection().execute(query):
            features.append((entry.filename,
                             np.loads(entry.feature_vector)))

        norms = []
        for fn, v in features:
            norms.append((np.linalg.norm(r_fv - v)))

        return [fn for fn, _ in sorted(norms, key=lambda (n, _): n)[:n]]


    def gen_tempfile(self):
        fn = '%s.jpg' % uuid.uuid1().get_hex()
        return open(fn, 'wb'), fn


    def safe_delete(self, filename):
        if os.path.isfile(filename):
            os.remove(filename)


    def from_raw_to_grayscale(self, raw):
        fp, fn = self.gen_tempfile()
        print >>fp, raw
        fp.close()

        img = cv2.imread(fn, cv2.CV_LOAD_IMAGE_GRAYSCALE)

        self.safe_delete(fn)

        return img


