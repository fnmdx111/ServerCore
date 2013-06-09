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
import sys


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
        return '<JPEGFileEntry %s %s %s>' % (self.id, self.uuid, self.fingerprint)



class ServerCore(object):
    DCT_CONTAINER_TYPE = np.float64
    GRAYSCALE_CONTAINER_TYPE = np.int16

    def __init__(self,
                 db_path='entries.db',
                 (size_h, size_w)=(480, 640)):
        self.db_path = db_path
        self.cwd = os.path.dirname(__file__).decode(sys.getfilesystemencoding())

        self.engine = create_engine('sqlite:///%s/%s' % (self.cwd, self.db_path))
        self.session = sessionmaker(bind=self.engine)()
        Base.metadata.create_all(self.engine)

        self.img_store_path = os.path.join(self.cwd, 'img_store')

        self.size_h = size_h
        self.size_w = size_w
        self.size_b_h = size_h / 8
        self.size_b_w = size_w / 8

        block_row_idx, block_col_idx = map(lambda end: range(0, end, 8), (size_h, size_w))
        self.block_coordinates = tuple(product(block_row_idx, block_col_idx))

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.results = []


    def add_entry(self, uuid, feature_vector, fingerprint):
        try:
            entry = JPEGFileEntry(uuid, feature_vector, fingerprint)
            self.session.add(entry)
            self.session.commit()
            return True, 'ok', ''
        except IntegrityError as err:
            self.session.rollback()
            if 'column fingerprint is not unique' in err.message:
                return False, 'err', 'This file is already in server.'


    def _dct_img(self, img):
        ret = np.ndarray((self.size_b_h, self.size_b_w),
                         dtype=np.dtype((self.DCT_CONTAINER_TYPE,
                                         (8, 8))))
        mat = np.zeros((8, 8), dtype=self.DCT_CONTAINER_TYPE)
        for r, c in self.block_coordinates:
            mat[:8, :8] = img[r:r + 8, c:c + 8]
            ret[r / 8, c / 8][:, :] = cv2.dct(mat)

        return ret


    def _extract_feat_vec(self, img, n=128):
        img = img.reshape((self.size_h * self.size_w / 64, 8, 8))

        return np.array(sorted(map(lambda dct: dct[0, 0], img),
                               reverse=True)[:n if n else None])


    def add_jpeg_file(self, data):
        img = self.from_raw_to_grayscale(base64.standard_b64decode(data))
        feature_vector = self._extract_feat_vec(self._dct_img(img))

        uuid_gen = uuid.uuid1().get_hex()
        flag, status, msg = self.add_entry(uuid_gen,
                                           feature_vector.dumps(),
                                           hashlib.sha1(data).hexdigest())
        if flag:
            cv2.imwrite('%s/img_store/%s.jpg' % (self.cwd, uuid_gen), img)

        return status, msg


    def prepare_results(self, data, n=10):
        img = self.from_raw_to_grayscale(base64.standard_b64decode(data))
        r_fv = self._extract_feat_vec(self._dct_img(img))

        features = []
        for entry in self.session.query(JPEGFileEntry):
            features.append((entry.uuid,
                             np.loads(entry.feature_vector)))

        norms = []
        for fn, v in features:
            norms.append((fn, np.linalg.norm(r_fv - v)))

        self.results = sorted(norms, key=lambda (_, n): n)[:n]

        return len(self.results)


    def retrieve(self):
        if self.results:
            return self.results.pop(0)
        else:
            return '', None


    def from_raw_to_grayscale(self, raw):
        return cv2.imdecode(np.fromstring(raw,
                                          dtype=np.uint8),
                            cv2.CV_LOAD_IMAGE_GRAYSCALE)


