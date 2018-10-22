@echo off
regsvr32 "C:\Program Files (x86)\obs-studio\bin\32bit\obs-virtualsource.dll"
regsvr32 "C:\Program Files (x86)\obs-studio\bin\64bit\obs-virtualsource.dll"
timeout 2
regsvr32 "C:\Program Files\obs-studio\bin\64bit\obs-virtualsource.dll"
regsvr32 "C:\Program Files\obs-studio\bin\32bit\obs-virtualsource.dll"
pause