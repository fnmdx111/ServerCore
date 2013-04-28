Server Core for Secure Image Retrieval System
=============================================

Requirement
-----------

* opencv - image manipulation
* numpy - backend for opencv
* sqlalchemy - interface for sqlite


Goal
----

* accept base64-encoded encrypted JPEG file
* retrieve similar JPEG file
* store feature vector's binary representation in sqlite, use uuid as filename and primary key


TODO
----

* add distance into the result
* enrich column, such as ownership(search in specified user id), description of image, etc.
* fix current working directory issue (fixed by using os.path.dirname(__file__))

License
-------

THIS PROJECT IS LICENSED UNDER GPL.


contact: chsc4698@gmail.com

