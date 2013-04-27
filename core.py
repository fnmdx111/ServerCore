# encoding: utf-8
import base64
import hashlib
from itertools import product
import logging
import os
import uuid
from sqlalchemy import Column, String, LargeBinary, create_engine, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np


Base = declarative_base()


class JPEGFileEntry(Base):
    __tablename__ = 'entries'

    _id = Column(Integer, primary_key=True)
    feature_vector = Column(LargeBinary)
    uuid = Column(String)
    fingerprint = Column(String, unique=True)

    def __init__(self, uuid, feature_vector, fingerprint):
        self.feature_vector = feature_vector
        self.uuid = uuid
        self.fingerprint = fingerprint


    def __repr__(self):
        return '<JPEGFileEntry %s>' % self.id



class ServerCore(object):
    DCT_CONTAINER_TYPE = np.int64
    GRAYSCALE_CONTAINER_TYPE = np.int16

    def __init__(self, db_path='entries.db',
                       (size_h, size_w)=(480, 640)):
        self.db_path = db_path

        print os.getcwd()
        self.engine = create_engine('sqlite:///%s/%s' % (os.getcwd(), self.db_path))
        self.session = sessionmaker(bind=self.engine)()
        Base.metadata.create_all(self.engine)

        self.size_h = size_h
        self.size_w = size_w
        self.size_b_h = size_h / 8
        self.size_b_w = size_w / 8

        block_row_idx, block_col_idx = map(lambda end: range(0, end, 8), (size_h, size_w))
        self.block_coordinates = tuple(product(block_row_idx, block_col_idx))

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)


    def add_entry(self, uuid, feature_vector, fingerprint):
        try:
            entry = JPEGFileEntry(uuid, feature_vector, fingerprint)
            self.session.add(entry)
            self.session.commit()
            return True
        except IntegrityError:
            return False


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
        img = img.reshape((self.size_h * self.size_w / 64, 8, 8))

        return np.array(sorted(map(lambda dct: dct[0, 0], img),
                               reverse=True)[:n if n else None])


    def add_jpeg_file(self, data):
        """@param img:numpy.ndarray: grayscale matrix"""
        img = self.from_raw_to_grayscale(base64.standard_b64decode(data))
        feature_vector = self._extract_feat_vec(self._dct_img(img))

        uuid_gen = uuid.uuid1().get_hex()
        succeeded = self.add_entry(uuid_gen,
                           feature_vector.dumps(),
                           hashlib.sha1(data).hexdigest())
        if not succeeded:
            return False

        cv2.imwrite('images/%s.jpg' % uuid_gen, img)
        return True


    def retrieve(self, data, n=10):
        """@param img:numpy.ndarray: grayscale matrix"""
        img = self.from_raw_to_grayscale(base64.standard_b64decode(data))
        r_fv = self._extract_feat_vec(self._dct_img(img))

        features = []
        for entry in self.session.query(JPEGFileEntry):
            features.append((entry.uuid,
                             np.loads(entry.feature_vector)))

        norms = []
        for fn, v in features:
            norms.append((fn, np.linalg.norm(r_fv - v)))

        return [fn for fn, _ in sorted(norms, key=lambda (_, n): n)[:n]]


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


