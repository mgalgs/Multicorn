# coding: utf8

import os
import sys
import shutil
import tempfile
import atexit
from unittest import TestCase

from kalamar import Site
from kalamar import Item

# There is some magic at the end of this file :-P

class TestData(object):
    _original_data = os.path.join(os.path.dirname(__file__), 'data')
    _dirname = None
    
    @classmethod
    def get(cls):
        if cls._dirname is None:
            atexit.register(cls.cleanup)
            cls._dirname = tempfile.mkdtemp()
        cls.mini_rsync(cls._original_data, cls._dirname)
        return cls._dirname
    
    @classmethod
    def mini_rsync(cls, src, dst):
        names = os.listdir(src)
        
        # remove files and dirs that aren’t in src
        for name in os.listdir(dst):
            dstname = os.path.join(dst, name)
            if name not in names:
                if os.path.isdir(dstname):
                    shutil.rmtree(dstname)
                else:
                    os.remove(dstname)

        for name in names:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            if os.path.isdir(srcname):
                if not os.path.isdir(dstname):
                    os.makedirs(dstname)
                cls.mini_rsync(srcname, dstname)
                shutil.copystat(srcname, dstname)
            else:
                try:
                    dststat = os.stat(dstname)
                except OSError:
                    pass
                else:
                    srcstat = os.stat(srcname)
                    if (srcstat.st_size, srcstat.st_mtime) == \
                       (dststat.st_size, dststat.st_mtime):
                        # the file is probably the same in src and dst: skip it
                        continue
                shutil.copy2(srcname, dstname)
        
    @classmethod
    def cleanup(cls):
        if cls._dirname is not None:
           shutil.rmtree(cls._dirname)
        

class TestSite(object):
    
    def setUp(self):
        self.temp_dir = TestData.get()
        self.site = Site(os.path.join(self.temp_dir, 'kalamar.conf'))
    

class TestSiteSearch(TestSite):
        
    def test_without_sugar(self):
        request = u'genre=jazz/artiste=Birelli Lagrène'
        for item in self.site.search(self.access_point_name, request):
            self.assertEqual(item.properties["genre"], u'jazz')
            self.assertEqual(item.properties["artiste"], u'Birelli Lagrène')
    
    def test_with_sugar(self):
        request = u'jazz/Birelli Lagrène'
        for item in self.site.search(self.access_point_name, request):
            self.assertEqual(item.properties["genre"], u'jazz')
            self.assertEqual(item.properties["artiste"], u'Birelli Lagrène')
    
    def test_all_data(self):
        request = u''
        all_objects = list(self.site.search(self.access_point_name, request))
        genres = set(item.properties["genre"] for item in all_objects)
        artistes = set(item.properties["artiste"] for item in all_objects)
        albums = set(item.properties["album"] for item in all_objects)
        
        self.assertEqual(len(all_objects), 20)
        self.assertEqual(genres, set([u'jazz', u'rock']))
        self.assertEqual(artistes, set([u"Jesus'harlem", u'Birelli Lagrène',
                                        u'Water please']))
        self.assertEqual(albums, set([u'manouche swing', u'S.O.B', u'alleluia',
                                      u'amen']))

class TestSiteOpen(TestSite):
    
    def test_no_result(self):
        request = u'genre=doesnt_exist'
        self.assertRaises(self.site.ObjectDoesNotExist, self.site.open,
                          self.access_point_name, request)
    
    def test_one_result(self):
        request = u'genre=rock/artiste=Jesus\'harlem/album=amen/titre=mechanical blues'
        item = self.site.open(self.access_point_name, request)
        self.assertEqual(item.properties['genre'], u'rock')
        self.assertEqual(item.properties['artiste'], u'Jesus\'harlem')
        self.assertEqual(item.properties['album'], u'amen')
        self.assertEqual(item.properties['titre'], u'mechanical blues')
    
    def test_many_results(self):
        request = u'genre=rock'
        self.assertRaises(self.site.MultipleObjectsReturned, self.site.open,
                          access_point, request)

class TestSiteSave(TestSite):
    
    def test_new_complete_item(self):
        access_point = self.site.access_points[self.access_point_name]
        if access_point.config['parser'] == 'audio_vorbis':
            vorbis_file = open(os.path.join(os.path.dirname(__file__),
                                        'data', 'vorbis_sample.ogg'))
            data = vorbis_file.read()
        else:
            data = ''
        properties = {'genre': 'funk',
                      'artiste': 'loopzilla',
                      'album': 'demo',
                      'titre': 'many money',
                      'piste': '2',
                      '_content': data}
        item = Item.create_item(access_point, properties)
        self.site.save(item)
        item2=self.site.open(self.access_point_name,
            u'genre=funk/artiste=loopzilla/album=demo/titre=many money/piste=2'
        )
        self.assertEqual(item2.properties['genre'], 'funk')
        self.assertEqual(item2.properties['artiste'], 'loopzilla')
        self.assertEqual(item2.properties['album'], 'demo')
        self.assertEqual(item2.properties['titre'], 'many money')
        self.assertEqual(item2.properties['piste'], '2')
        
    def test_new_incomplete_item(self):
        """Should raise an Exception ?"""
        pass # TODO
    
    def test_unmodified_item(self):
        pass # TODO
    
    def test_modified_item(self):
        pass # TODO

class TestSiteRemove(TestSite):
    def test_remove(self):
        request = u'genre=rock/artiste=Jesus\'harlem/album=amen/titre=cross'
        item = self.site.open(self.access_point_name, request)
        self.site.remove(item)
        self.assertEqual(list(self.site.search(self.access_point_name, request)), [])

# Magic tricks
site = Site(os.path.join(os.path.dirname(__file__), 'data', 'kalamar.conf'))

for access_point in site.access_points:
    for test in (TestSiteSearch, TestSiteOpen, TestSiteSave, TestSiteRemove):
        cls = type(test.__name__+'_'+access_point, (test, TestCase),
                   {"access_point_name": access_point})
        setattr(sys.modules[__name__], cls.__name__, cls)

