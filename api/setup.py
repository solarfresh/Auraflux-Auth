from setuptools import setup
from Cython.Build import cythonize
import os
import shutil


# This script sets up the OCR API project using setuptools and Cython.
# It compiles Cython extensions for performance, particularly in image processing tasks.
# It organizes the project structure, ensuring that necessary directories are created and cleaned up.
# The 'app' package contains the main application logic, including API endpoints, core functionality,
# models, services, and utilities.
PACKAGE_LIST = [
    'agents',
    'iam',
    'messaging',
    'users'
]

# Create the build directory if it doesn't exist, and clean up any previous builds.
# The build directory is used to store compiled Cython files and other build artifacts.
# The script ensures that the current working directory is set correctly and that the build path is created
# before proceeding with the build process.
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# Ensure the build directory exists and is clean.
# The build directory is where compiled Cython files will be placed.
# It is created if it does not exist, and any previous build artifacts are removed.
BUILD_PATH = os.path.join(CURRENT_PATH, 'build')
os.makedirs(BUILD_PATH, exist_ok=True)

# The script iterates over the list of packages, copying each package's contents to the build directory.
# It also renames Python files to Cython files (with a .pyx extension)
# and removes any test files to prepare for the build process.
# The Cython files will be compiled into C extensions for performance optimization.
# The 'cythonize_list' will hold the paths to the Cython files that need to be compiled.
cythonize_list = []
for package in PACKAGE_LIST:
    package_path = os.path.join(CURRENT_PATH, package)
    build_path = os.path.join(BUILD_PATH, package)
    if os.path.exists(build_path):
        shutil.rmtree(build_path)

    shutil.copytree(package_path, build_path)

    for root, _, fnames in os.walk(build_path):
        pyx_counter = 0
        for fname in fnames:
            if fname.lower().endswith('_test.py'):
                os.remove(os.path.join(root, fname))
                continue

            if (not fname.lower().endswith('.py')) or (fname == '__init__.py') or ('migrations' in root):
                continue

            pyx_file = f'{os.path.splitext(fname)[0]}.pyx'
            os.rename(
                os.path.join(root, fname),
                os.path.join(root, pyx_file)
            )
            pyx_counter += 1

        if not pyx_counter:
            continue

        cythonize_list.append(f'{root}/*.pyx')

setup(
    name="auraflux_nexus",
    ext_modules=cythonize(
       cythonize_list,
        compiler_directives={
            'language_level': "3",
            'binding': True,
            'annotation_typing': False
        }
    )
)

print("remove *.pyx, *.pyc, and *.c file")
for root, _, fnames in os.walk(CURRENT_PATH):
    for fname in fnames:
        if not fname.lower().endswith(('.pyx', '.pyc', '.c')):
            continue

        os.remove(os.path.join(root, fname))

shutil.rmtree("build", ignore_errors=True)
