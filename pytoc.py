#!/usr/bin/python3
# -*- coding: utf-8 -*-
#import os
import sys
import subprocess
import platform

__version__ = "1.0.0"

forbidden_characters = [";", ",", "[", "]", "(", ")", "#", "!", "<", ">","\\", ":", "?", "*", "'", '"', "&"]


#this main function does check, creates and cleans if requested
def main(argList):
    setup = "setup.py"
    filename, filename_py, filename_pyx, filename_c, filename_o = generateAllFilenames(argList)
    isKeeping = checkParameter('-K', argList)
    #removes the temp files only if "-K" or "--keep" parameter is not used it's the default behaviour removing the temp files
    if not isKeeping:
        isKeeping = checkParameter('--keep', argList)
    isLibrary = checkParameter('-L', argList) 
    if not isLibrary:
        isLibrary = checkParameter('--library', argList)      
    checkPrerequisites()
    if isLibrary:
        createLibrary(filename, filename_py, filename_pyx)
    else:        
        createExe(filename, filename_py, filename_pyx, filename_c, filename_o)
    if not isKeeping:
        cleanupFiles(setup, filename_pyx, filename_c, filename_o, isLibrary)


#this function generate all extensions used by this program and return them
def generateAllFilenames(argList):
    filename = argList[0]
    filename_py = filename + '.py'
    filename_pyx = filename + '.pyx'    
    filename_c  = filename + '.c'
    filename_o = filename + '.o'
    filename_so = filename + '.so'
    return filename, filename_py, filename_pyx, filename_c, filename_o

#return true if parameter found in argList otherwise False
def checkParameter(parameter, argList):
    isFound = False
    if parameter in argList:
        isFound = True
    return isFound

#this function check if all pre-requisites exist on the system 
#normally the requirements.txt will contain all needed dependencies but in case of we try to execute without these dependencies
# we check that
def checkPrerequisites():
        #check if python3 is installed
    stdout, stderr = checkCommandInstalled('python3')
    if 'python3' not in stdout:
        return print("python3 is required! Please install it!")
    #check if cython3 is installed
    stdout, stderr = checkCommandInstalled("cython3")
    if 'cython3' not in stdout:
        return print("cython3 is required! Please install it!")
    #check if gcc is installed
    stdout, stderr = checkCommandInstalled("gcc")
    if 'gcc' not in stdout:
        return print("gcc is required! Please install it!") 


#this function create the exe step by step : generate file.pyx, generate file.c, generate file.o and eventually exe file 
def createExe(filename, filename_py, filename_pyx, filename_c, filename_o):
    stdout = ""
    stderr = ""
    #copy file.py to file.pyx
    stdout, stderr = copieTo(filename_py, filename_pyx)
    if stderr != "":
        return print("issue during copie " + stderr)
    #create the setup.py for cython        
    stdout, stderr = createSetupPy(filename_pyx)   
    if stderr != "":
        return print("issue during setup.py creation " + stderr)
    #cython3 creates the c output with main function       
    stdout, stderr = createCOutput(filename_pyx) 
    if stderr != "":
        return print("issue during C source creation " + stderr)
    python_version = retrieve_python_version()    
    #use gcc to create the object    
    stdout, stderr = createObjFromC(filename_c, filename_o, python_version)   
    if stderr != "":
        return print("issue during object creation " + stderr)
    #use gcc to create the exe        
    stdout, stderr = createExeFromObj(filename, filename_o, python_version) 
    if stderr != "":
        return print("issue during exe creation " + stderr)    


#this function create the shared library step by step : generate file.pyx, generate file.c, generate file.o and eventually file.so 
def createLibrary(filename, filename_py, filename_pyx):
    stdout = ""
    stderr = ""
    #copy file.py to file.pyx
    stdout, stderr = copieTo(filename_py, filename_pyx)
    #insert cython compiler directive line using sed 
    stdout, stderr = insertCythonDirective(filename_pyx) 
    if stderr != "":
        return print("issue during insert cython directive " + stderr)
    #create the setup.py for cython        
    stdout, stderr = createLibSetupPy(filename, filename_pyx)   
    if stderr != "":
        return print("issue during setup.py creation " + stderr)
    #cython3 creates the c output with main function       
    stdout, stderr = createLibOutput() 
    if stderr != "":
        return print("issue during library creation " + stderr)


#this function removes temp files created by this program
#transferring in arguments a list of temp files to remove file.pyx file.c file.o    
def cleanupFiles(setup, filename_pyx, filename_c, filename_o, isLibrary):
    filenameList = []
    filenameList.append(setup)
    filenameList.append(filename_pyx)
    filenameList.append(filename_c)
    if not isLibrary:
        filenameList.append(filename_o)
    stdout, stderr = cleanupTempFiles(filenameList)
    if isLibrary:
        dirList = []
        dirList.append('build')
        stdout, stderr = cleanupBuildDir(dirList)
    if stderr != "":
        return print("issue during cleaning step " + stderr) 

# return the result of which    
def checkCommandInstalled(command):
    stdout = ""
    stderr = ""
    parmList = []
    parmList.append('which')
    parmList.append(command)
    stdout, stderr = execute(parmList)
    return stdout, stderr

#insert using sed : sed -i '1s/^/your text\n/' file   
def insertCythonDirective(filename_pyx):
    parmList = []
    parmList.append('sed')
    parmList.append('-i')
    parmList.append('1 i#cython: language_level=3\n')
    parmList.append(filename_pyx)
    #print(parmList)
    stdout, stderr = execute(parmList)
    return stdout, stderr
    #sed -i '1 i\anything' file

#generic copy file function
def copieTo(filename_from, filename_to):
    parmList = []
    parmList.append('cp')
    parmList.append(filename_from)
    parmList.append(filename_to)
    stdout, stderr = execute(parmList)
    return stdout, stderr

#create the setup.py used by cython3
def createSetupPy(filename_pyx):
    stdout = ""
    stderr = ""
    filecontent = "from setuptools import setup\nfrom Cython.Build import cythonize\n" + 'setup(ext_modules = cythonize("' + filename_pyx + '"))'
    try:
        f = open("setup.py", "w")
        f.write(filecontent)
        f.close()
        stdout = "setup.py created successfully"
    except IOError:
        stderr = "I/O on setup.py creation"
    return stdout, stderr


#create the setup.py used by cython3
def createLibSetupPy(filename, filename_pyx):
    stdout = ""
    stderr = ""
    filecontent = "from distutils.core import setup\nfrom distutils.extension import Extension\nfrom Cython.Distutils import build_ext\n" \
    + 'ext_modules = [Extension("' + filename + '", ["' + filename_pyx + '"])]\n' + "setup(name = '" + filename + "', cmdclass = {'build_ext': build_ext}," \
    + "ext_modules = ext_modules)"
    #print(filecontent)
    try:
        f = open("setup.py", "w")
        f.write(filecontent)
        f.close()
        stdout = "setup.py created successfully"
    except IOError:
        stderr = "I/O on setup.py creation"
    return stdout, stderr


#create the file.c from the file.pyx using cython3 and setup.py
def createCOutput(filename_pyx):
    parmList = []
    parmList.append('cython3')
    parmList.append(filename_pyx)
    parmList.append('--embed')
    parmList.append('-X language_level=3')
    stdout, stderr = execute(parmList)
    return stdout, stderr

#create the library file.c from the file.pyx using cython3 and setup.py
def createLibOutput():
    parmList = []
    parmList.append('python3')
    parmList.append('setup.py')
    parmList.append('build_ext')    
    parmList.append('--inplace')
    stdout, stderr = execute(parmList)
    return stdout, stderr


#create the file.o from file.c using gcc
def createObjFromC(filename_c, filename_o, python_version):
    parmList = []
    parmList.append('gcc')
    parmList.append('-o')
    parmList.append(filename_o)
    parmList.append('-I/usr/include/python' + python_version)
    parmList.append('-lpython' + python_version)
    parmList.append('-c')
    parmList.append(filename_c) 
    #print(parmList)
    stdout, stderr = execute(parmList)
    return stdout, stderr

#create the file (exe) from file.o using gcc
def createExeFromObj(filename, filename_o, python_version):
    parmList = []
    parmList.append('gcc')
    parmList.append('-o')
    parmList.append(filename)
    parmList.append(filename_o)
    parmList.append('-I/usr/include/python' + python_version)
    parmList.append('-lpython' + python_version)
    stdout, stderr = execute(parmList)
    return stdout, stderr

#remove temp files
def cleanupTempFiles(filenameList):
    parmList = []
    parmList.append('rm')
    for filename in filenameList:
        parmList.append(filename)  
    stdout, stderr = execute(parmList)
    return stdout, stderr

#remove build directory
def cleanupBuildDir(dirList):
    parmList = []
    parmList.append('rm')
    parmList.append('-rf')
    for dir in dirList:
        parmList.append(dir)  
    stdout, stderr = execute(parmList)
    return stdout, stderr

#execute a command and arguments received in parmList
def execute(parmList):
    stdout = ""
    stderr = ""
    process = subprocess.Popen(parmList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()
    return stdout, stderr

# retrieve the python version that will use for gcc needs
def retrieve_python_version():
    python_version = platform.python_version()
    #print(python_version)
    python_major, python_minor, python_revision = python_version.split('.')
    #print(python_major, python_minor, python_revision)
    python_version_maj_min = python_major + "." + python_minor
    #print(python_version_maj_min)
    return python_version_maj_min

#this function prints the help
def pytoc_print_help():
    print("PyToC is a python3 compiler for code written in the python language.")
    print("PyToC uses Python3, Cython3 and gcc.")
    print("For linux and linux-like OS that have the pre-requisites")
    print("Usage: pytoc [options] filename")
    print("filename is the basename without extension, the filename.py should exist in the current directory")
    print("Options:")
    print("-V, --version        Display version number of PyToC compiler")
    print("-H, --help           Display this help")
    print("-K, --keep           keeps all intermediate files generated by the compiler")
    print("-L, --library        Generate filename.so shared library instead of an exe")
    print("__________________________________________")
    print("Enjoy!")


#starting code
if __name__ == "__main__":
    argList = []
    isForbid = False
    # execute only if run as a script
    #print(f"Arguments count: {len(sys.argv)}")
    argList = sys.argv[1:]
    nbarg = len(argList)
    for i, arg in enumerate(argList):
        matched_list = [characters in forbidden_characters for characters in arg]
        #print(matched_list)
        if True in matched_list:
            isForbid = True
            print("forbidden characters found! retry without them")
            break
    if not isForbid:            
        if nbarg == 0:
            print("missing arguments! filename required!")         
        else:        
            argFirst = argList[0]
            if argFirst.lower() == '--help' or argFirst.lower() == '-h':
                pytoc_print_help()
            elif argFirst.lower() == '--version' or argFirst.lower() == '-v':
                print("PyToC version " + __version__)    
            else:                        
                main(argList)
                print("done!")