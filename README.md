# MoveVideo
Simple Python script that identifies video files by name and move into a directory with the same name.
Usefull for organize newly files into directory tree.

The tag from filename is just the prefix until "." character
The tag from directories is from directory name with "." character as separetor.

Ex:
filename AAA.Test1.mkv -> tag = AAA
filename BBB.Test1.mkv -> tag = BBB
directory AAA.BBB -> tags = AAA e BBB

The program move both files AAA.Test1.mkv and BBB.Test1.mkv to AAA.BBB directory
