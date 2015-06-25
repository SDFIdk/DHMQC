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
import os
import tempfile
import subprocess

    
def get_local_file(remote_path):
    ext=os.path.splitext(remote_path)[1]
    f=tempfile.NamedTemporaryFile(suffix=ext,delete=False)
    f.close()
    os.unlink(f.name) #now we have a unique name, nice :-)
    if remote_path.startswith("s3://"):
        cmd="aws s3 cp {0:s} {1:s}".format(remote_path,f.name)
    elif remote_path.startswith("http://"):
        cmd="curl -o {0:s} {1:s}".format(f.name,remote.path)
    else:
        raise Exception("Remote 'protocol' not supported: "+remote_path)
    rc=subprocess.call(cmd)
    assert(rc==0)
    assert(os.path.exists(f.name))
    return f.name

        