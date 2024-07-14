cmake_minimum_required (VERSION 2.8.11)
project (test-decode)
set(CMAKE_BUILD_TYPE Debug)

add_executable (test-decode audiofile.cpp bufferaviocontext.cpp bufferdecodeoutput.cpp decodeoutput.cpp filedecodeoutput.cpp referencedata.cpp test-decode.cpp)
set_target_properties(test-decode PROPERTIES CXX_STANDARD 17)

target_compile_definitions(test-decode PRIVATE DEBUG=0)

target_include_directories (test-decode PUBLIC /usr/include/ffmpeg)
target_link_libraries (test-decode LINK_PUBLIC avcodec avformat avutil swresample boost_program_options)

add_executable (test-getinfo audiofile.cpp bufferaviocontext.cpp bufferdecodeoutput.cpp decodeoutput.cpp filedecodeoutput.cpp referencedata.cpp test-getinfo.cpp)
set_target_properties(test-getinfo PROPERTIES CXX_STANDARD 17)
target_compile_definitions(test-getinfo PRIVATE DEBUG=0)

target_include_directories (test-getinfo PUBLIC /usr/include/ffmpeg)
target_link_libraries (test-getinfo LINK_PUBLIC avcodec avformat avutil swresample boost_program_options)
