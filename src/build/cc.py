# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import sys
IS_WINDOWS=sys.platform.startswith("win")
IS_MAC="darwin" in sys.platform
#TODO: add more options and or methods like optimized_high/low and more or less pedantic....
class ccompiler(object):
	COMPILER=""
	LINKER=""
	IS_MSVC=False
	COMPILE_LIBRARY_RELEASE=[]
	COMPILE_LIBRARY_DEBUG=[]
	COMPILE_EXE_RELEASE=[]
	COMPILE_EXE_DEBUG=[]
	LINK_LIBRARY_RELEASE=[]
	LINK_LIBRARY_DEBUG=[]
	LINK_EXE_RELEASE=[]
	LINK_EXE_DEBUG=[]
	DEFINE_SWITCH=""
	INCLUDE_SWITCH=""
	IMPLIB_EXT=""
	LINK_OUTPUT_SWITCH=""
	LINK_LIBRARIES=""
	VERSION_SWITCH=""
	DEF_FILE_SWITCH=""
	IMPLIB_SWITCH=""
	OBJ_EXTENSION=""
	def overrideCompiler(self,cc,linker=None):
		self.COMPILER=cc
		if linker is None:
			self.LINKER=cc
		else:
			self.LINKER=linker
	def getOptions(self,is_library=True,is_debug=False):
		if is_library:
			if is_debug:
				return self.COMPILE_LIBRARY_DEBUG,self.LINK_LIBRARY_DEBUG
			else:
				return self.COMPILE_LIBRARY_RELEASE,self.LINK_LIBRARY_RELEASE
		else:
			if is_debug:
				return self.COMPILE_EXE_DEBUG,self.LINK_EXE_DEBUG
			else:
				return self.COMPILE_EXE_RELEASE,self.LINK_EXE_RELEASE
	def linkOutput(self,outname):
		return [self.LINK_OUTPUT_SWITCH+outname] #works for everything but MAC gcc!

class sunc(ccompiler):
	COMPILER="cc"
	LINKER="cc"
	ALL_BUILD=["-c"]
	COMPILE_LIBRARY_RELEASE=ALL_BUILD+["-O3","-fpic"]
	COMPILE_LIBRARY_DEBUG=ALL_BUILD+["-g","-O1","-fpic"]
	COMPILE_EXE_RELEASE=ALL_BUILD+["-O3"]
	COMPILE_EXE_DEBUG=ALL_BUILD+["-g","-O1"]
	LINK_LIBRARY_RELEASE=["-shared"]
	LINK_LIBRARY_DEBUG=["-shared"]
	LINK_EXE_RELEASE=[]
	LINK_EXE_DEBUG=[]
	LINK_LIBRARIES=["-lm"]
	DEFINE_SWITCH="-D"
	INCLUDE_SWITCH="-I"
	LINK_OUTPUT_SWITCH="-o"
	OBJ_EXTENSION=".o"


class sunc32(sunc):
	sunc.ALL_BUILD+["-m64"]
	
class sunc64(sunc):
	ALL_BUILD=sunc.ALL_BUILD+["-m64"]
	
#core gcc class
class gcc(ccompiler):
	COMPILER="gcc"
	LINKER="gcc"
	ALL_BUILD=["-c", "-W", "-Wall", "-Wextra", "-Wno-long-long" , "-pedantic"]
	COMPILE_LIBRARY_RELEASE=ALL_BUILD+["-O3"]
	COMPILE_LIBRARY_DEBUG=ALL_BUILD+["-g","-O"]
	COMPILE_EXE_RELEASE=ALL_BUILD+["-O3"]
	COMPILE_EXE_DEBUG=ALL_BUILD+["-g","-O"]
	LINK_LIBRARY_RELEASE=["-shared"]
	LINK_LIBRARY_DEBUG=["-shared"]
	LINK_EXE_RELEASE=[]
	LINK_EXE_DEBUG=[]
	DEFINE_SWITCH="-D"
	INCLUDE_SWITCH="-I"
	IMPLIB_EXT=".a"
	LINK_OUTPUT_SWITCH="-o"
	LINK_LIBRARIES=[]
	DEF_FILE_SWITCH=""
	IMPLIB_SWITCH=""
	OBJ_EXTENSION=".o"

#gcc subvariants
class mingw32(gcc):
	LINK_LIBRARY_RELEASE=gcc.LINK_LIBRARY_RELEASE+["-Wl,--kill-at"]
	LINK_LIBRARY_DEBUG=gcc.LINK_LIBRARY_DEBUG+["-Wl,--kill-at"]
	LINK_LIBRARIES=["-lkernel32","-luser32","-lgdi32","-lwinspool","-lshell32","-lole32","-loleaut32","-luuid","-lcomdlg32","-ladvapi32"]

class gcc_nix(gcc):
	COMPILE_LIBRARY_RELEASE=gcc.COMPILE_LIBRARY_RELEASE+["-fPIC"]
	COMPILE_LIBRARY_DEBUG=gcc.COMPILE_LIBRARY_DEBUG+["-fPIC"]
	LINK_LIBRARIES=["-lm"]

class mingw64(mingw32):
	COMPILER="x86_64-w64-mingw32-gcc.exe"
	LINKER="x86_64-w64-mingw32-gcc.exe"
	LINK_LIBRARIES=[]  #TODO - add relevant 64 bit version

class macports_gcc(gcc_nix):
	COMPILER="/opt/local/bin/gcc-mp-4.6"
	LINKER="/opt/local/bin/gcc-mp-4.6"

class gcc_mac(gcc_nix):
	def linkOutput(self,outname):
		return [self.LINK_OUTPUT_SWITCH,outname] 

class msvc(ccompiler):
	COMPILER="cl"
	LINKER="link"
	IS_MSVC=True
	ALL_BUILD=["/c","/D_WINDOWS","/W3","/Zm1000","/TC","/fp:precise","/D_CRT_SECURE_NO_WARNINGS"]
	COMPILE_LIBRARY_RELEASE=ALL_BUILD+["/MD","/O2","/Ob2","/DNDEBUG"]
	COMPILE_LIBRARY_DEBUG=ALL_BUILD+["/D_DEBUG","/MDd","/Zi","/Ob0","/Od","/RTC1"]
	#USE SAME RUNTIME FOR EXE PROGRAMS... WILL NOT WANT TO CROSS RUNTIME BOUNDARIES WITH STUFF LIKE FILE POINTERS
	COMPILE_EXE_RELEASE=COMPILE_LIBRARY_RELEASE
	COMPILE_EXE_DEBUG=COMPILE_LIBRARY_DEBUG
	LINK_LIBRARY_RELEASE=["/DLL", "/INCREMENTAL:NO"]
	LINK_LIBRARY_DEBUG=["/DLL","/debug","/INCREMENTAL"]
	LINK_EXE_RELEASE=["/INCREMENTAL:NO"]
	LINK_EXE_DEBUG=["/debug","/INCREMENTAL"]
	LINK_OUTPUT_SWITCH="/out:"
	EXE_OUTPUT_SWITCH="/Fe"
	DEFINE_SWITCH="/D"
	INCLUDE_SWITCH="/I"
	VERSION_SWITCH=""
	DEF_FILE_SWITCH="/def:"
	IMPLIB_SWITCH="/implib:"
	IMPLIB_EXT=".lib"
	OBJ_EXTENSION=".obj"
	#STANDARD BUILD OPTIONS
	LINK_LIBRARIES=[]
	
class msvc32(msvc):
	LINK_LIBRARIES=["kernel32.lib","user32.lib","gdi32.lib","winspool.lib","shell32.lib","ole32.lib","oleaut32.lib",
	"uuid.lib","comdlg32.lib","advapi32.lib"]

class msvc64(msvc):
	LINK_LIBRARIES=[] #TODO: add relevant 64bit libraries....
	
