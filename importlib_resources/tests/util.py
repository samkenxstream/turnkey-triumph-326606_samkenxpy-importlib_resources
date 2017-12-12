import abc
import importlib
import io
import sys
import types
import unittest

from .. import abc as resources_abc
from . import data01
from . import zipdata01
from .._compat import ABC, Path, PurePath, FileNotFoundError


try:
    from importlib.machinery import ModuleSpec
except ImportError:
    ModuleSpec = None                               # type: ignore


def create_package(file, path, is_package=True, contents=()):
    class Reader(resources_abc.ResourceReader):
        def open_resource(self, path):
            self._path = path
            if isinstance(file, Exception):
                raise file
            else:
                return file

        def resource_path(self, path_):
            self._path = path_
            if isinstance(path, Exception):
                raise path
            else:
                return path

        def is_resource(self, path_):
            self._path = path_
            if isinstance(path, Exception):
                raise path
            for entry in contents:
                parts = entry.split('/')
                if len(parts) == 1 and parts[0] == path_:
                    return True
            return False

        def contents(self):
            if isinstance(path, Exception):
                raise path
            # There's no yield from in baseball, er, Python 2.
            for entry in contents:
                yield entry

    name = 'testingpackage'
    # Unforunately importlib.util.module_from_spec() was not introduced until
    # Python 3.5.
    module = types.ModuleType(name)
    if ModuleSpec is None:
        # Python 2.
        module.__name__ = name
        module.__file__ = 'does-not-exist'
        if is_package:
            module.__path__ = []
    else:
        # Python 3.
        loader = Reader()
        spec = ModuleSpec(
            name, loader,
            origin='does-not-exist',
            is_package=is_package)
        module.__spec__ = spec
        module.__loader__ = loader
    return module


class CommonTests(ABC):

    @abc.abstractmethod
    def execute(self, package, path):
        raise NotImplementedError

    def test_package_name(self):
        # Passing in the package name should succeed.
        self.execute(data01.__name__, 'utf-8.file')

    def test_package_object(self):
        # Passing in the package itself should succeed.
        self.execute(data01, 'utf-8.file')

    def test_string_path(self):
        # Passing in a string for the path should succeed.
        path = 'utf-8.file'
        self.execute(data01, path)

    @unittest.skipIf(sys.version_info < (3, 6), 'requires os.PathLike support')
    def test_pathlib_path(self):
        # Passing in a pathlib.PurePath object for the path should succeed.
        path = PurePath('utf-8.file')
        self.execute(data01, path)

    def test_absolute_path(self):
        # An absolute path is a ValueError.
        path = Path(__file__)
        full_path = path.parent/'utf-8.file'
        with self.assertRaises(ValueError):
            self.execute(data01, full_path)

    def test_relative_path(self):
        # A reative path is a ValueError.
        with self.assertRaises(ValueError):
            self.execute(data01, '../data01/utf-8.file')

    def test_importing_module_as_side_effect(self):
        # The anchor package can already be imported.
        del sys.modules[data01.__name__]
        self.execute(data01.__name__, 'utf-8.file')

    def test_non_package_by_name(self):
        # The anchor package cannot be a module.
        with self.assertRaises(TypeError):
            self.execute(__name__, 'utf-8.file')

    def test_non_package_by_package(self):
        # The anchor package cannot be a module.
        with self.assertRaises(TypeError):
            module = sys.modules['importlib_resources.tests.util']
            self.execute(module, 'utf-8.file')

    @unittest.skipIf(sys.version_info < (3,), 'No ResourceReader in Python 2')
    def test_resource_opener(self):
        bytes_data = io.BytesIO(b'Hello, world!')
        package = create_package(file=bytes_data, path=FileNotFoundError())
        self.execute(package, 'utf-8.file')
        self.assertEqual(package.__loader__._path, 'utf-8.file')

    @unittest.skipIf(sys.version_info < (3,), 'No ResourceReader in Python 2')
    def test_resource_path(self):
        bytes_data = io.BytesIO(b'Hello, world!')
        path = __file__
        package = create_package(file=bytes_data, path=path)
        self.execute(package, 'utf-8.file')
        self.assertEqual(package.__loader__._path, 'utf-8.file')

    def test_useless_loader(self):
        package = create_package(file=FileNotFoundError(),
                                 path=FileNotFoundError())
        with self.assertRaises(FileNotFoundError):
            self.execute(package, 'utf-8.file')


class ZipSetupBase:
    ZIP_MODULE = None

    @classmethod
    def setUpClass(cls):
        data_path = Path(cls.ZIP_MODULE.__file__)
        data_dir = data_path.parent
        cls._zip_path = str(data_dir / 'ziptestdata.zip')
        sys.path.append(cls._zip_path)
        cls.data = importlib.import_module('ziptestdata')

    @classmethod
    def tearDownClass(cls):
        try:
            sys.path.remove(cls._zip_path)
        except ValueError:
            pass

        try:
            del sys.path_importer_cache[cls._zip_path]
            del sys.modules[cls.data.__name__]
        except KeyError:
            pass

        try:
            del cls.data
            del cls._zip_path
        except AttributeError:
            pass


class ZipSetup(ZipSetupBase):
    ZIP_MODULE = zipdata01                          # type: ignore
