# Video info
Displays frame rate, resolution, codec etc. of a video file
```>> ffprobe test_.mp4
ffprobe version 5.1.1 Copyright (c) 2007-2022 the FFmpeg developers
  built with clang version 14.0.6
  configuration: --prefix=/d/bld/ffmpeg_1662055343048/_h_env/Library --cc=clang.exe --cxx=clang++.exe --nm=llvm-nm --ar=llvm-ar --disable-doc --disable-openssl --enable-demuxer=dash --enable-hardcoded-tables --enable-libfreetype --enable-libfontconfig --enable-libopenh264 --ld=lld-link --target-os=win64 --enable-cross-compile --toolchain=msvc --host-cc=clang.exe --extra-libs=ucrt.lib --extra-libs=vcruntime.lib --extra-libs=oldnames.lib --strip=llvm-strip --disable-stripping --host-extralibs= --enable-gpl --enable-libx264 --enable-libx265 --enable-libaom --enable-libsvtav1 --enable-libxml2 --enable-pic --enable-shared --disable-static --enable-version3 --enable-zlib --pkg-config=/d/bld/ffmpeg_1662055343048/_build_env/Library/bin/pkg-config
  libavutil      57. 28.100 / 57. 28.100
  libavcodec     59. 37.100 / 59. 37.100
  libavformat    59. 27.100 / 59. 27.100
  libavdevice    59.  7.100 / 59.  7.100
  libavfilter     8. 44.100 /  8. 44.100
  libswscale      6.  7.100 /  6.  7.100
  libswresample   4.  7.100 /  4.  7.100
  libpostproc    56.  6.100 / 56.  6.100
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'test_.mp4':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2avc1mp41
    encoder         : Lavf59.27.100
  Duration: 00:00:10.01, start: 0.000000, bitrate: 2569 kb/s
  Stream #0:0[0x1](und): Video: h264 (High 4:4:4 Predictive) (avc1 / 0x31637661), yuv444p(progressive), 600x540, 2549 kb/s, 199.88 fps, 199.88 tbr, 1000k tbn (default)
    Metadata:
      handler_name    : VideoHandler
      vendor_id       : [0][0][0][0]
      encoder         : Lavc59.37.100 libx264
```

# Video compression
Convert video file reduce its file size
`ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4`
The compression is controlled with `-crf 23` (lossless: 0, worst quality: 51, default: 23).
The codec is specified with `-c:v libx264`.
TODO: benchmark compression for DLC learning.

## process multiple files
Loop over all `.mp4` files, call `ffmpeg` and replace original file (Windows CMD for loop)
```FOR %i IN (*.mp4) DO (ffmpeg -i %i -c:v libx264 -crf 23 tmp.mp4 && move tmp.mp4 %i)```
