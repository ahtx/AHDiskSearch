# This package is tested with the followings:

## Install packages/dependencies
* [Python3.8.10](https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe) `remember to check add to path while installing`
* py -3.8 -m venv test_env
* python -m pip install pip --upgrade
* python -m pip install wheel --upgrade
* pip install -r requirements.txt --no-cache-dir
* pip install ttkbootstrap --no-warn-conflicts

## External dependencies
* Download [ffmpeg](https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2021-11-09-12-23/ffmpeg-n4.4.1-2-gcc33e73618-win64-lgpl-4.4.zip)
* extract the zip file and copy bin content to `ttkbootstrap` folder. `required fo audio to text conversion`
* [resnet50_coco_best_v2.1.0.h5](https://github.com/OlafenwaMoses/ImageAI/releases/download/essentials-v5/resnet50_coco_best_v2.1.0.h5/) after downloading move this to `ttkbootstrap` folder. `required for object detection`

### Facing the following issue ?
`ImportError: Could not find the DLL(s) 'msvcp140_1.dll'. TensorFlow requires that these DLLs be installed in a directory that is named in your %PATH% environment variable. You may install these DLLs by downloading "Microsoft C++ Redistributable for Visual Studio 2015, 2017 and 2019" for your platform from this URL: https://support.microsoft.com/help/2977003/the-latest-supported-visual-c-downloads`
* Download and install [vc_redist.x64.exe](https://aka.ms/vs/16/release/vc_redist.x64.exe)
