import os
import re
from kofoto.outputengine import OutputEngine

css = '''
body {
    color: #000000;
    background: #dddddd;
    font-family: Verdana, Geneva, Arial, Helvetica, sans-serif;
    font-size: 10pt;
}

img {
    border-style: none;
    display: block;
}

img.thinborder {
    color: #000000; /* Netscape */
    border-color: #000000; /* IE */
    border-style: solid;
    border-width: 1px;
}

img.toc {
    color: #000000; /* Netscape */
    border-color: #000000; /* IE */
    border-style: solid;
    border-width: 1px;
    margin-top: 0.3cm;
}

img.icon {
    display: inline;
}

a.toc {
    display: block;
}

td.arrow {
    font-size: 9pt;
}

a:link {
    color: #24238e;
}

a:visited {
    color: #6b4789;
}

.textleft {
    padding-right: 10pt;
}

.header {
    font-size : 10pt;
    background: #c5c2c0;
    table-layout: fixed;
    border-style: solid;
    border-width: 1px;
    border-color: #000000;
}

.photographer {
    font-size: 9pt;
}

.footer {
    font-size : 9pt;
}

h1 {
    font-size : 15pt;
    margin-bottom: 10px;
}

h2 {
    font-size: 10pt;
}

td.info {
    background: #c5c2c0;
    border-style: solid;
    border-width: 1px;
    border-color: #000000;
}
'''

transparent_1x1_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV\xca\x00\x00\x00\x03PLTE\xff\xff\xff\xa7\xc4\x1b\xc8\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\x01bKGD\x00\x88\x05\x1dH\x00\x00\x00\nIDATx\xdac`\x00\x00\x00\x02\x00\x01\xe5\'\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82'

frame_bottom_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x11\x08\x06\x00\x00\x00\x1c\xc3\xc6\x12\x00\x00\x001IDATx\xda\x8d\xc9A\r\x000\x0c\x03\xb1S\x07\'$\x072*\x8abHGa\xfe\x1aI\xc6vH\xb2\x05P\xdd\xcd\x99\x99\x8b\xed\xfd\x8cE\x92\x01\xf4\x00#%(P\xc8\xc2\x05\'\x00\x00\x00\x00IEND\xaeB`\x82"

frame_bottomleft_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x0c\x00\x00\x00\x11\x08\x03\x00\x00\x00\xde\xe3\xbd\x90\x00\x00\x00?PLTE\xff\xff\xffVVV\xd4\xd4\xd4\xfe\xfe\xfe\xdb\xdb\xdbNNN+++\xff\xff\xff\xf8\xf8\xf8UUU\xfd\xfd\xfd\xb1\xb1\xb1\xd3\xd3\xd3OOO999GGG222###\xb0\xb0\xb0\x07\x07\x07***]\xe6\x12X\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00WIDATx\xdau\xcbI\x12\x80 \x0cD\xd1f\x08\x88\xa2\x12\xe0\xfegUIQ\xc6\x85o\xf7+\x1d\x18\xeb\x9c\xa70\xe0\x8e\xb8x;\x8c\x88N \xd9\xd5M\xa0-\xdb\tfO\x86\x0e2\x0f\x0c\xa7\x9c%H\x1e%JV\xc1U\xcd\x1a\xf7\x10\n\xe1\xc5UE\xcf\x7f\xf1\x995\x86v\x01N\xe0\x02\xcf\xcf?\xc7w\x00\x00\x00\x00IEND\xaeB`\x82'

frame_bottomright_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x11\x08\x06\x00\x00\x00;mG\xfa\x00\x00\x00\xd2IDATx\xda\xa5\x931\n\x840\x10E\x7f\x96@\xbc\x84\x95\x9d\xb9\x8b\xa5\x17\xd9\xde\xc2\xde\xdb\x05\x1b\x89U\x0e\xb1c\x91\xbf\xcd\xba\xac\xacY\x8d;\x10Bf\xe0\xc1<\xf2\xd14\xcdc\x9a&\xc6\x18\x19c\xa4s\x8em\xdb\xd29w\xd4\x8b\xd6Z\x07\xc0\xde\x86a0eYB)\x85\xab\xa5\xab\xaa\xfa\x0b\x00\x00\x1a\x00Hb\xef>\r\x19\xc7\xf1\xfd \x89y\x9e!\"y\x90\xbe\xef7\x90eYP\x14\x05\x8c1\xe7!]\xd7}5\x8d1Xe\x9fYM\xd7u\xbd;\xc8\x91\xadS\x83\x1c\xd9\x1b\xb1)\xd8\x91\xec\x8d\xd8\x14\xe4H\xf6\xae\xd8\xbd\xfa%;)6G\xb6\xce\xf9T\x9f\x92\xd7\xb3\x8aenVH\xc2{O\x11!\x00\xaaW\x9c\xb3!\"\xc2\x10\x82\x17\x91\xbb\x02`/\x86\x97\x00\x04@x\x02\xb7\x89\xa5\xf8\x0b\xe9\xfe\xce\x00\x00\x00\x00IEND\xaeB`\x82"

frame_left_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x06\x00\x00\x00\x01\x08\x06\x00\x00\x00\xfd\xc9\xdf\xf0\x00\x00\x00\x1fIDATx\xda\x05\xc1\x01\x01\x00\x00\x08\xc20\xfb\xd0\x87\xe4\xcfs\xdc\xae-\x80\xea\xd4\x01&\xe1\x01\xe4\xbc\x12\x12\xcbp\xe9\x92\x00\x00\x00\x00IEND\xaeB`\x82"

frame_right_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x01\x08\x06\x00\x00\x008\xbbEa\x00\x00\x00(IDATx\xda\x85\xc8A\x01\x000\x10\xc20\xfc\xe0\xe7\x94WO\x99\x84\xe5\x99\xb4\x05P\x9d:`w7`\x9f\xb3-I\xfa\x00N\xd33\x8ef\xbf\xfbs\x00\x00\x00\x00IEND\xaeB`\x82"

frame_top_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x06\x08\x06\x00\x00\x00\x02\x10\xf41\x00\x00\x00$IDATx\xda\x05\xc1\x01\x11\x00\x00\x08\x02\xb1?\xeb\xd8\x87\xe4\x1cq\xd0\rI\xc6vi{\x030I\x8e\xdd\xf5\x03\xe1\xef\x0e$\xd4\n|5\x00\x00\x00\x00IEND\xaeB`\x82"

frame_topleft_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x06\x00\x00\x00\x06\x08\x06\x00\x00\x00\xe0\xcc\xefH\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\tpHYs\x00\x00\x0b\x12\x00\x00\x0b\x12\x01\xd2\xdd~\xfc\x00\x00\x00\x07tIME\x07\xd3\x05\x01\x0e3\x1b\\\xb2\xad\xe2\x00\x00\x00TIDATx\x9c]\x89\xb1\r\xc0 \x10\x03m\x84`\x0f\xbe\"\x03\xb1\x00#\xb0Xv\xfa%pE*\xa2\x90\x93\\\xf8\x8e\xad\xb5[\x92\xa5\x94H\x12\x9b8\xe7\xb4\xde\xfbUJ9C\xce\x99f\xc6Z\xeb\x11\xc2>$\xdf\x01@\xc4\x0fIpw\x84\xaf\\k\xc1\xdd1\xc6\xd0\x03E\xd4\x18G\xcb:X\x17\x00\x00\x00\x00IEND\xaeB`\x82"

frame_toprightlower_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x06\x08\x03\x00\x00\x00\x12`\x85\xeb\x00\x00\x00BPLTE\xff\xff\xffVVVUUUOOO\xd4\xd4\xd4\xd3\xd3\xd3\xb1\xb1\xb1NNN\xfe\xfe\xfe\xfd\xfd\xfd\xff\xff\xff\xdb\xdb\xdb\xf8\xf8\xf8999HHH222###\x07\x07\x07+++\xb0\xb0\xb0***$$$\xfe%C\x19\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x000IDATx\xdac\x10b\xe1\xe0`agce\x15\x16`\x80\x00\xb0\x08\x13\x0b\'\'\xab\x08\xb2\x08#\x88\x10"B\x84_TDD@\x10Y\x04j<\x00\x81\xe6\x02\x97\xe5V\x02\x01\x00\x00\x00\x00IEND\xaeB`\x82'

frame_toprightupper_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x06\x08\x03\x00\x00\x00\x12`\x85\xeb\x00\x00\x00BPLTE\xff\xff\xffVVVUUUOOO\xd4\xd4\xd4\xd3\xd3\xd3\xb1\xb1\xb1NNN\xfe\xfe\xfe\xfd\xfd\xfd\xff\xff\xff\xdb\xdb\xdb\xf8\xf8\xf8999HHH222###\x07\x07\x07+++\xb0\xb0\xb0***$$$\xfe%C\x19\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x007IDATx\xdaU\xcbK\x0e\x00\x10\x10\x04QC3\xed\xcf\xfd/Kbcj\xf9\x92r"\xe2\x83\xb8/\x001\xe9/$3\xbc\x91Rh\xa5\xb6+\xe6\xd2J\xa2\x0f\x9dk?8-\x01\x01%!\xee\xc5\x0e\x00\x00\x00\x00IEND\xaeB`\x82'

previous_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x01;PLTE\xff\xff\xff\x00\x00\x00\x10\x00\x1d\x04\x00\x07\x1b\x134CCn\x17\x03&\x16\x112P_\x91ov\xa6 \x0e-\x13\x0f2GZ\x8f\x83\x92\xca\x85\x8a\xba7+J$\x110#\x101#\x10/\x1f\x0b*\x06\x00\t\x16\x0f>GY\x92~\x8e\xc9\x97\xa0\xd8\x97\x9d\xd4\x8d\x8e\xc0\x8c\x8c\xbb\x8a\x8a\xbb\x89\x89\xba\x88\x88\xb9\x8b\x8b\xbauq\x9c\x17\x0e3PY\x91\x7f\x8e\xc8\x92\x9d\xd5\x97\x9e\xd6\x96\x9f\xd7\x98\x9f\xd7\x98\xa1\xd7\x99\xa0\xd8}}\xb2 \r.\n\x04)7I\x84n\x7f\xbf\x84\x92\xcf\x87\x95\xd0\x86\x94\xcf\x86\x95\xcf\x84\x94\xcf\x83\x93\xce\x85\x93\xd0\x84\x90\xcflp\xa9\x1a\n+\x00\x00\r\x0e\x17O1M\x96Db\xafIf\xb2Jh\xb3Ic\xb0Jd\xb1BM\x95\x11\x00)\x03\x00!\x12"c&?\x91-J\x9c.K\x9f.H\x9f-H\x9e0J\x9f/>\x8a\r\x00%\x10\x1ea";\x8d*D\x99+E\x9a)D\x9a(B\x99+B\x9a,;\x87\x0b\x00#%=\x94\x1c.\x7f\x19+z\x1d/|!,n\x08\x00\x1d!9\x8a\x1a/}\x08\x030\x04\x00\x1b\x07\x00\x19\x00\x00\x03\x0e\x1c_\x13"n\x04\x00\x19\x03\x00\x1f\t\x10F\x01\x00\x11\x00\x00\x01\x9e\xfe\x9a\x98\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\xc8IDATx\xdac`\xa0#`\xc4!\xce\xc4\x8c]\x9c\x85\x95\r\xab8;\x07\'\x176qn\x1e^>~\x01\x01AA!!\x01 \x06\x02a\x11\x90\xb8\xa8\x98\xb8\x84\xa4\x94\xb4\xb4\x8c\xac\x9c<\x98\x90\x95S\x10\x06\x8a+*)\xabH\xa8\xaa\xa9khhh\x82\t\r\ru-m\x06\x06\x1d]=}\x03\x03\x03C#c\x13}S0a\xa2ofn\xc1`iemck\x07\x04\xb6@`\x0f%\x1c\x1c\x9d\x18\x18\x9c]\\\xdd\xdc!\xc0\xc3\xd3\x03Lxxy\xfb\x00\xedp\xf6\xf5\xf3\x0f\x08\x0cB\x06\xc1!\xa1\x0c\x10\x99\xa0\xb0\xf0\x08$\x10\x19\x15\xcd\x00\x91\x89\x89\x8d\x8bG\x06\t\x89\x10\x1f:\'%\xa7`\x0f\xab\xd4\xb4t\x1c\xa1k\x99Aj|P\x01\x00\x00\x8d\xc20#(\x85\x17q\x00\x00\x00\x00IEND\xaeB`\x82'

noprevious_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x00\x9cPLTE\xff\xff\xff\x7f\x7f\x7f\xac\xac\xac\x96\x96\x96\xbf\xbf\xbf\x89\x89\x89\xa0\xa0\xa0\xc9\xc9\xc9\xba\xba\xba\x84\x84\x84\x9c\x9c\x9c\xc6\xc6\xc6\x8f\x8f\x8f\xa5\xa5\xa5\xcf\xcf\xcf\xb0\xb0\xb0\x82\x82\x82\xa3\xa3\xa3\x87\x87\x87\xaf\xaf\xaf\x8b\x8b\x8b\x9e\x9e\x9e\x91\x91\x91\xa8\xa8\xa8\xb2\xb2\xb2\x81\x81\x81\x98\x98\x98\xa2\xa2\xa2\xcb\xcb\xcb\xbc\xbc\xbc\xc8\xc8\xc8\xd1\xd1\xd1\x80\x80\x80\xad\xad\xad\x97\x97\x97\xc0\xc0\xc0\x8a\x8a\x8a\xa1\xa1\xa1\xca\xca\xca\x85\x85\x85\x9d\x9d\x9d\xc7\xc7\xc7\x90\x90\x90\xd0\xd0\xd0\xb1\xb1\xb1\x83\x83\x83\xa4\xa4\xa4\x88\x88\x88\x8c\x8c\x8c\x9f\x9f\x9f\x92\x92\x92\xb3\xb3\xb38\x0cY\x9f\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\xaeIDATx\xda\xbd\x91K\x0f\x820\x10\x84\x17\xb4.X\xf1\x11\xa3\xd2\x82<\x14\xd0\nT\xd0\xff\xff\xdf,\x8f\x03$\xe5`b\xfc\x0es\x98\xd9\xec&\xb3\x00\x7f\xc4\x98\xf0\xcbH\xefW\xbb\x9b\xd6O\xf6\xe7D\xe7\x13\x13)\xaf\x86\x90vsb\x8a0\xc7 \x10\x94\x8aV(\xb5H3\x1f\x8bu\x98\xe7\xe1\x90\xab\xdal\xcb9\xfa\xbe\x9fe\x19b\'\x88h=!\xaa\x9c\x8d\xfbV\xb8\x8a\xa2\x97\xe2d\x03\xb0c-\x9d\x0e)e+\xd2Y\x94\xea\x06{\xdc=\xcfKG\x1c\x9a\xa0I\xd2\x9a\xcf\x06\xf0\xcb\x16\xbad\xc9m6\xa2\xaf\x8e\xad^L\xdf\x15#\x13%Bd|\xfb\x8f\x1f\xf0\x01g\xef\x16\xef\xde#\x0cr\x00\x00\x00\x00IEND\xaeB`\x82'

next_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x01;PLTE\xff\xff\xff\x00\x00\x00\x04\x00\x07\x10\x00\x1d\x17\x03&CCn\x1b\x134 \x0e-ov\xa6P_\x91\x16\x112\x06\x00\t\x1f\x0b*#\x10/#\x101$\x1107+J\x85\x8a\xba\x83\x92\xcaGZ\x8f\x13\x0f2uq\x9c\x88\x88\xb9\x89\x89\xba\x8b\x8b\xba\x8a\x8a\xbb\x8c\x8c\xbb\x8d\x8e\xc0\x97\x9d\xd4\x97\xa0\xd8~\x8e\xc9GY\x92\x16\x0f> \r.}}\xb2\x98\x9f\xd7\x98\xa1\xd7\x99\xa0\xd8\x96\x9f\xd7\x97\x9e\xd6\x92\x9d\xd5\x7f\x8e\xc8PY\x91\x17\x0e3\x1a\n+lp\xa9\x84\x90\xcf\x84\x92\xcf\x83\x93\xce\x85\x93\xd0\x84\x94\xcf\x86\x95\xcf\x86\x94\xcf\x87\x95\xd0n\x7f\xbf7I\x84\n\x04)\x11\x00)BM\x95Jd\xb1If\xb2Ic\xb0Jh\xb3Db\xaf1M\x96\x0e\x17O\x00\x00\r\r\x00%/>\x8a0J\x9f.H\x9f-H\x9e.K\x9f-J\x9c&?\x91\x12"c\x03\x00!\x0b\x00#,;\x87+B\x9a(B\x99)D\x9a+E\x9a*D\x99";\x8d\x10\x1ea\x08\x00\x1d!,n\x1d/|\x19+z\x1c.\x7f%=\x94\x00\x00\x03\x07\x00\x19\x04\x00\x1b\x08\x030\x1a/}!9\x8a\x04\x00\x19\x13"n\x0e\x1c_\x01\x00\x11\t\x10F\x03\x00\x1f\x00\x00\x017\xd36x\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\xc8IDATx\xdac`\xa0?`\xc4%\xc1\xc4\x8cC\x82\x85\x95\r\xbb\x04;\x07\'\x17\x84\xc5\xcd\xc3\x0b\x02|\xfc@\xcc\xc7\xcf/ ($,\x02\x96\xe0\x11\x15\x13\x97\x10\x13\x97\x94\x02\x13R\xd22\xb2r\xf2\n \tE%e\x15\x15U\x15\x15\x15e0\xa1\xa6.\xab\xa1\xa9\xa5\r\x94\xd0\xd1\xd5\xd370\xd4702\x06\x13&\xa6\xa6\xa6\xfaf\xe6\x16\x0c\x0c\x96V\xd666\xb666P\xc2\x0e\x08l\xec\x1d\x1c\x9d\x18\x9c]\\\xdd\xdc\xdc\xdd<<\xc0\x04\x18xzy\xfb00\xf8\xfa\xf9\x07 \x83\xc0\xa0\xe0\x90P\xa08CXxD$\x12\x88\x8a\x0e\x80\x883\xc4\xc4\xc6!\x83\xf8\x84D\x888:HJN\xc1*\xce\x90\x9a\x96\x8e=\xac2\x9cH\x8d\x0f\n\x00\x00-\xb5/\xc3\xf0)\x85[\x00\x00\x00\x00IEND\xaeB`\x82'

nonext_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x00\x9cPLTE\xff\xff\xff\x7f\x7f\x7f\xac\xac\xac\x96\x96\x96\xbf\xbf\xbf\x89\x89\x89\xa0\xa0\xa0\xc9\xc9\xc9\xba\xba\xba\x84\x84\x84\x9c\x9c\x9c\xc6\xc6\xc6\x8f\x8f\x8f\xa5\xa5\xa5\xcf\xcf\xcf\xb0\xb0\xb0\x82\x82\x82\xa3\xa3\xa3\x87\x87\x87\xaf\xaf\xaf\x8b\x8b\x8b\x9e\x9e\x9e\x91\x91\x91\xa8\xa8\xa8\xb2\xb2\xb2\x81\x81\x81\x98\x98\x98\xa2\xa2\xa2\xcb\xcb\xcb\xbc\xbc\xbc\xc8\xc8\xc8\xd1\xd1\xd1\x80\x80\x80\xad\xad\xad\x97\x97\x97\xc0\xc0\xc0\x8a\x8a\x8a\xa1\xa1\xa1\xca\xca\xca\x85\x85\x85\x9d\x9d\x9d\xc7\xc7\xc7\x90\x90\x90\xd0\xd0\xd0\xb1\xb1\xb1\x83\x83\x83\xa4\xa4\xa4\x88\x88\x88\x8c\x8c\x8c\x9f\x9f\x9f\x92\x92\x92\xb3\xb3\xb38\x0cY\x9f\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\xa9IDATx\xda\xbd\x91\xcd\x0e\x820\x10\x84\x17\xb4\x96Z\xebO\x8cJ\x0b\x02jA\x11\x8b\xa0\xef\xffn\xd6\xc2\x01\x0c=\x18\x13\xbfL\xe60\x93\xb9\xec\x02\xfc\x1f\xc7V$\xcaR\x9cW\xd5p!\xf7k\xd9nQ\xd5EP\xec"S \x8f\xd2\\+2\x16\xe1"\xce]\xb3\x91\xa7\xb8KQ\xc4\xf3\xfc\xf0\xde\xdc=\x8cq\xa6\x955\x16\x86!\x1e\x97\x04\x80\xecn\xbe\xaf\xd5\xdaS\xe3/X\x95\x80\x9a\xb0R\xc3\x981CYo9\x80\xda\xa4=\x82 \xb8\\u\x0e\xcb\xa3\x18u\x10u\xda\xe4\xe0\xf0\x1eDL\x9b\xfc\x13\xfe\x98\xf1\xe1#"n9{\xf2\xed?~\xe0\x05|9\x16\xef\xde\x00\xf7B\x00\x00\x00\x00IEND\xaeB`\x82'

smaller_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x01ePLTE\xff\xff\xff\x1e\x1e9\x1a\x1a1\x18\x18-\x16\x16)\x1b\x1b2\x1b\x1b4IIxZZ\xb5ii\xc6hh\xc3WW\xb0@@m\x12\x12#\x10\x10\x1f\x16\x16+<<g}}\xd6\x83\x83\xda\x82\x82\xd9||\xd5uu\xd0__\xba..Q\n\n\x15\x14\x14%JJ{\x87\x87\xdc\x90\x90\xe1\x9d\x9d\xe8\xa6\xa6\xed\xaa\xaa\xef\xa8\xa8\xed\x9a\x9a\xe7\x85\x85\xdcqq\xcc::c\x08\x08\x11\x13\x13$88a\x80\x80\xd7\x8b\x8b\xde\xad\xad\xf0\xb3\xb3\xf2\xb5\xb5\xf2\xb1\xb1\xf0\x95\x95\xe6vv\xd1\'\'H\x11\x11"nn\xc9\x89\x89\xde\xb1\xb1\xf2\xb6\xb6\xf3\xa8\xa8\xef\xa2\xa2\xeb\x98\x98\xe7bb\xbd\x07\x07\x0f\x0f\x0f\x1eEEr\xb8\xb8\xf3\xa4\xa4\xed\x9b\x9b\xe855\\\x05\x05\n\x0b\x0b\x16``\xbb\x8b\x8b\xe0\xac\xac\xefVV\xaf\x03\x03\x06\t\t\x12yy\xd2\x93\x93\xe4((I))J\xa3\xa3\xectt\xcdzz\xd3\x97\x97\xe6\'\'F\x9f\x9f\xea\x95\x95\xe4pp\xc9\x02\x02\x05\x05\x05\x0b]]\xb8\x85\x85\xdaRR\xa5\x01\x01\x02;;d\x8d\x8d\xe0\xa1\xa1\xea\x9d\x9d\xea\x88\x88\xdd\x00\x00\x00\x8e\x8e\xe1\x7f\x7f\xd6##@11V{{\xd4\x81\x81\xd8mm\xc8\x01\x01\x03\x1c\x1c5TT\xadqq\xcakk\xc6RR\x9f\x18\x18/\x00\x00\x01KK\x82UU\xaeJJ}$$AAAnKK\x80""?\xdf\xa4f\xa0\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x01;IDATx\xdac` \x00\x18\x99\x98YXX0\x84Y\xd9\xd898\xb9\xb8yx\xf9P\xc5\xf9\x058\x05\x85\x84\x84ED\xc5\xc4%\x90\xc5%\xa5\x04\xa5ed\xe5\xe4\x15\x14\x95\x94UT\x11\xe2j\xea\x1a\x9a\x8aZ\xda:\xda\xbaZrz\xfa\x06\x08\x19C#cY\x13\x1dSS\x1d\x1d]3s\x0bK+\x98\xb8\xb5\x8d\x92\x9e\x96\xb6\xa9\xad\xad\xa9\x8e\x89\x96\x9d\xbd\x8c\x83#T\xc2\xc9\xd9\xc5N\xcbD\x07$\xa1\xeb\n\x94ps\x87Jxxz\xc9iy{\xfb\xf8\xf8x\x1b\x18\xf8*\xca\xf8\xc1$\xac\xfc\x03\xcc\xcd\x0c\xbc\x81\xc0\xc0 0(X3$\x14*\x11\x16\xae\'\xeb\xab\xe0\xaa\xa5\xa5%/gn!\x13\x11\x19\x05\x95p\x8c\x8e\xd1\xb3\x8f\xb5\x93\x93\xb3\xf3\x8d\xb3\x90\x89\x17\x14O\x809\xcb\x91\xd3E&@\xd1\xde^6\xc0+1>\x89#\n\xee\x0f\xf7d\r\xa5\xf8D\x99D\x19\x17c!\x11e\xd6\x04\x84\xd7CS\xf4S\x934\xd2\x92\x92D\xf4\xd3}\x12\x90\x03+#3+[\x19\x08rr\xf3\x12\x12Pd\xf23\x02\x0b\n\x0b\x8b\x8a\x81\xa2\thR\t\t0\x11^^T\x19\x84\x92\x12F\\2\xa5e8\xf5\x18b\x97`\xc0\xa1\x01\x02\x00\\\x80@\x88\x10gev\x00\x00\x00\x00IEND\xaeB`\x82'

nosmaller_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x00\xf3PLTE\xff\xff\xff\x7f\x7f\x7f\xaf\xaf\xaf\x97\x97\x97\xc7\xc7\xc7\xbb\xbb\xbb\xa4\xa4\xa4\xd3\xd3\xd3\x8b\x8b\x8b\x85\x85\x85\xb5\xb5\xb5\x9d\x9d\x9d\xcd\xcd\xcd\xc1\xc1\xc1\xd9\xd9\xd9\xac\xac\xac\x92\x92\x92\x82\x82\x82\xb3\xb3\xb3\x9a\x9a\x9a\xbe\xbe\xbe\xd6\xd6\xd6\x8e\x8e\x8e\x88\x88\x88\xb8\xb8\xb8\xa1\xa1\xa1\xd0\xd0\xd0\xc4\xc4\xc4\xdc\xdc\xdc\xca\xca\xca\xa7\xa7\xa7\x94\x94\x94\x81\x81\x81\xb1\xb1\xb1\x99\x99\x99\xc9\xc9\xc9\xbd\xbd\xbd\xa6\xa6\xa6\xd5\xd5\xd5\x8d\x8d\x8d\x87\x87\x87\x9f\x9f\x9f\xcf\xcf\xcf\xc3\xc3\xc3\xdb\xdb\xdb\xae\xae\xae\x84\x84\x84\x9c\x9c\x9c\xc0\xc0\xc0\xd8\xd8\xd8\x90\x90\x90\x8a\x8a\x8a\xba\xba\xba\xd2\xd2\xd2\xc6\xc6\xc6\xde\xde\xde\x80\x80\x80\x98\x98\x98\xc8\xc8\xc8\xbc\xbc\xbc\xd4\xd4\xd4\x8c\x8c\x8c\x9e\x9e\x9e\xce\xce\xce\xc2\xc2\xc2\xad\xad\xad\x93\x93\x93\x83\x83\x83\xb4\xb4\xb4\xbf\xbf\xbf\xd7\xd7\xd7\x8f\x8f\x8f\x89\x89\x89\xb9\xb9\xb9\xa2\xa2\xa2\xd1\xd1\xd1\xc5\xc5\xc5\xdd\xdd\xdd\xcb\xcb\xcb\xa8\xa8\xa8\x95\x95\x95\xec#\\\x17\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x01\x15IDATx\xda\x85\x90kS\x82@\x14@Y\'\x0bKI\xaa\x85\x02cu\xa0-yTN\x81\x88\x18\x94\x82\x10\xb8\xf9\xff\x7fM\x94<\xa4b:\x1f\xcf\xb9wf\xefR\xd4?\xaco\x174M\xff\xd2\x1cw3\x8a/[W\x11_\xf7\xf48\xf6\xd34\xf5\x83\xd5\xac\xb3\xef\x9f$\xff\x80\x98p\x12\n\x96\xf2\xb2\xac|t"\xca\x023\xd8\x0ct\x06z\x01\xaa\n\xdfvL}\xf3\x85\x1e\xba\xeaq\x19\xee\x0e-/\x9b\x9fN\xb3\xc0\xe0\x84<\xb0y\xe8\xacd\xcc\xe8Uh\r\xf3p\xff\xd8\x85\xcc\xf6\x1b\x84\xb0@.\x8a\xb0\xec\xa9n\x88v\x1e\x1dy\xf2\xdc\xce\x03{\xe6\x998d2&\xd0U\x89\xf5Z\x86\xf1\xb5\x97\xb8\x18B\x8cM\x958\xfe\x0c\x14\xcfbc\x99\xa8B\x92\x98j\x978\xda\xc8.\xef\x18\xf6E\xcb!\x19\xb2\x93\xfa\n\x07\xaa\xd3\xed\xf3\xa0\xa7\x89\xa2\xa6\xf9A{\x0b\xf6?\xcb\xe6\x8c\xb9\x92\xf1|\xba\x00\xa0V\x80\x8d>\x0cCz\xcb,\xf8\x99@a\xa2\xa8^\xaa\x91\xf7uS\x91\xfa\x8d;\xfc\xdf\x81jX\xd8\xf1\t\xda/.\x11\x05E\x18\xfa\x00\x00\x00\x00IEND\xaeB`\x82'

larger_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x01hPLTE\xff\xff\xff\x1e\x1e9\x1a\x1a1\x18\x18-\x16\x16)\x1b\x1b2\x1b\x1b4IIxZZ\xb5ii\xc6hh\xc3WW\xb0@@m\x12\x12#\x10\x10\x1f\x16\x16+<<g}}\xd6\x83\x83\xda\x82\x82\xd9||\xd5uu\xd0__\xba..Q\n\n\x15\x14\x14%JJ{\x87\x87\xdc\x90\x90\xe1\x9d\x9d\xe8\xa6\xa6\xed\xaa\xaa\xef\xa8\xa8\xed\x9a\x9a\xe7\x85\x85\xdcqq\xcc::c\x08\x08\x11\x13\x13$88a\x80\x80\xd7\x8b\x8b\xde\xad\xad\xf0\xb3\xb3\xf2\xb5\xb5\xf2\xb1\xb1\xf0\x95\x95\xe6vv\xd1\'\'H\x11\x11"nn\xc9\x89\x89\xde\xb1\xb1\xf2\xb6\xb6\xf3))J\xa8\xa8\xef\xa2\xa2\xeb\x98\x98\xe7bb\xbd\x07\x07\x0f\x0f\x0f\x1eEEr\xb8\xb8\xf3\xa4\xa4\xed\x9b\x9b\xe855\\\x05\x05\n\x0b\x0b\x16``\xbb\x8b\x8b\xe0\xac\xac\xefVV\xaf\x03\x03\x06\t\t\x12yy\xd2\x93\x93\xe4((I\xa3\xa3\xectt\xcdzz\xd3\x97\x97\xe6\'\'F\x9f\x9f\xea\x95\x95\xe4pp\xc9\x02\x02\x05\x05\x05\x0b]]\xb8\x85\x85\xdaRR\xa5\x01\x01\x02;;d\x8d\x8d\xe0\xa1\xa1\xea\x9d\x9d\xea\x88\x88\xdd\x00\x00\x00%%D\x8e\x8e\xe1\x7f\x7f\xd6##@11V{{\xd4\x81\x81\xd8mm\xc8\x01\x01\x03\x1c\x1c5TT\xadqq\xcakk\xc6RR\x9f\x18\x18/\x00\x00\x01KK\x82UU\xaeJJ}$$AAAnKK\x80""?S\xe4\xb0\xf5\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x01:IDATx\xdac` \x00\x18\x99\x98YXX0\x84Y\xd9\xd898\xb9\xb8yx\xf9P\xc5\xf9\x058\x05\x85\x84\x84ED\xc5\xc4%\x90\xc5%\xa5\x04\xa5ed\xe5\xe4\x15\x14\x95\x94UT\x11\xe2j\xea\x1a\x9a\x8aZ\xda:\xda\xbaZrz\xfa\x06\x08\x19C#cY\x13\x1dS33\x1d]s\x0bK+k\x98\xb8\x8d\xad\x92\x9e\x96\xb6\xa9\x1dP\xc2D\xcb\xdeA\xc6\xd1\t*\xe1\xec\xe2j\xafe\xa2\x03\x92\xd0u\x03J\xb8{@%<\xbd\xbc\xe5\xb4||\xcc\xcc\xcc|\x0c\x0c|\x15e\xfc`\x12\xd6\xfe\x01\x16\xe6\x06>@``\x10\x18\x14\xac\x19\x12\n\x95\x08\x0b\xd7\x93\xf5Up\xd320\x90\x97\xb3\xb0\x94\x89\x88\x8c\x82J8E\xc7\xe89\xc4\xda\xcb\x05\x06\xfa\xc6Y\xca\xc4\x0b\x8a\'\xc0\x9c\xe5\xc4\xe9*\x13\xa0\xe8\x90\x98\x18\xe0\x9d\x14\x9f\xcc\x11\x05\xf7\x87G\x8a\x86R|\x92L\x92\x8c\xab\xb1\x90\x882k\x02\xc2\xeb\xa1\xa9\xfai\xc9\x1a\xe9\xc9\xc9"\xfa\x19f\t\xc8\x81\x95\x99\x95\x9d\xa3\x0c\x04\xb9y\xf9\t\t(2\x05\x99\x81\x85EE\xc5%@\xd1\x044\xa9\x84\x04\x98\x08//\xaa\x0cBI)#.\x99\xb2r\x9cz\x0c\xb1K0\xe0\xd0\x00\x01\x00\x0e7A6+\xddR\n\x00\x00\x00\x00IEND\xaeB`\x82'

nolarger_png = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xd7\xa9\xcd\xca\x00\x00\x00\xf3PLTE\xff\xff\xff\x7f\x7f\x7f\xaf\xaf\xaf\x97\x97\x97\xc7\xc7\xc7\xbb\xbb\xbb\xa4\xa4\xa4\xd3\xd3\xd3\x8b\x8b\x8b\x85\x85\x85\xb5\xb5\xb5\x9d\x9d\x9d\xcd\xcd\xcd\xc1\xc1\xc1\xd9\xd9\xd9\xac\xac\xac\x92\x92\x92\x82\x82\x82\xb3\xb3\xb3\x9a\x9a\x9a\xbe\xbe\xbe\xd6\xd6\xd6\x8e\x8e\x8e\x88\x88\x88\xb8\xb8\xb8\xa1\xa1\xa1\xd0\xd0\xd0\xc4\xc4\xc4\xdc\xdc\xdc\xca\xca\xca\xa7\xa7\xa7\x94\x94\x94\x81\x81\x81\xb1\xb1\xb1\x99\x99\x99\xc9\xc9\xc9\xbd\xbd\xbd\xa6\xa6\xa6\xd5\xd5\xd5\x8d\x8d\x8d\x87\x87\x87\x9f\x9f\x9f\xcf\xcf\xcf\xc3\xc3\xc3\xdb\xdb\xdb\xae\xae\xae\x84\x84\x84\x9c\x9c\x9c\xc0\xc0\xc0\xd8\xd8\xd8\x90\x90\x90\x8a\x8a\x8a\xba\xba\xba\xd2\xd2\xd2\xc6\xc6\xc6\xde\xde\xde\x80\x80\x80\x98\x98\x98\xc8\xc8\xc8\xbc\xbc\xbc\xd4\xd4\xd4\x8c\x8c\x8c\x9e\x9e\x9e\xce\xce\xce\xc2\xc2\xc2\xad\xad\xad\x93\x93\x93\x83\x83\x83\xb4\xb4\xb4\xbf\xbf\xbf\xd7\xd7\xd7\x8f\x8f\x8f\x89\x89\x89\xb9\xb9\xb9\xa2\xa2\xa2\xd1\xd1\xd1\xc5\xc5\xc5\xdd\xdd\xdd\xcb\xcb\xcb\xa8\xa8\xa8\x95\x95\x95\xec#\\\x17\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x01\x18IDATx\xda\x85\xd0\xedR\x82@\x18\x05`\xd6\xc9\xc2\xd2M*\xa0\xc0X\x1d\x88\x92\x8f\xca)\x08\x11\x83P\x10\x026\xee\xffj\xa2\xe4C*\xa7\xf3\xf3<\xef\xbb\xb3\xbb\x04\xf1O6\xb7K\x92$\x7f\xd5\x0cs3\x89/;W\x11\xdb\xee\xc9i\xec\xa5i\xea\x05\xebyo\xb7\x7f\x12\xbc\x03l\xd0\xb3\x903\xa5\xd7U\xd3G\'\xbc\xc8\xc1Q6\xd2 \xed\x06\xa8\x11\xb6k\x1bZ\x96\xe5y\xa6\x85\x8er\\\xc3\xdd\xa1\xe9\x16\xf3/_\x00\xe5\x04?P%\xf4\xd6\xa2\x0c\xb5\x06:\xe3\x12\xee\x1f\xfb4\xcc\xbf\x83\x90\xcc\xe1\x8b\nV\x03\xc5\t\xd1\xb6GG\xae\xb8\xb0J\xa0\xce\\C\x0e!DhF;\n6\xdfj\x98^\xbb\x89#\xd3\xc59\x86\x82mo\x0e\xaakQ\xb1\x88\x15.\xf1}\xa5\x8fmub\xd5\xef\x18\x0fy\xd3\xc6ED;\xf5$\x064O\xb7\xce\x83\x81\xca\xf3\xaa\xea\x05\xdd\x1c\xec~\x96\xc5\xe8\x0b\xa9\xc8\xf3\xe9\x12\x80\x96\x00\x0b}\xe8\xba\xe0\x17-\xf8I\xa0j\xa2\xa8-\xcd\xc8\xfbf\x9f\x08\xc3\xbd;\xec\xdf@\xecY\xd8\xe6\x13m\xda.x\xed\x89\x8d\x00\x00\x00\x00\x00IEND\xaeB`\x82'

album_template = '''<?xml version="1.0" encoding="%(charenc)s"?>
<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=%(charenc)s" />
<link href="woolly.css" type="text/css" rel="stylesheet" />
<title>%(title)s</title>
</head>
<body>
<table cellpadding="3" width="85%%" align="center" cellspacing="0">
<tr><td class="header">%(paths)s</td></tr>
<tr>
<td>
<h1 class="title">%(title)s</h1>
%(description)s
</td>
</tr>
<tr>
<td align="center">
<table cellpadding="20">
%(subalbumentries)s
%(imageentries)s
</table>
</td>
</tr>
<tr>
<td class="footer" colspan="3">
<p>&nbsp;</p>
<hr>
<small>%(blurb)s</small>
</td>
</tr>
</table>
</body>
</html>
'''

thumbnails_frame_template = '''<?xml version="1.0" encoding="%(charenc)s"?>
<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=%(charenc)s" />
<link rel="stylesheet" href="../woolly.css" type="text/css" />
</head>
<body>
%(entries)s
</body>
</html>
'''

# At least Opera 6.12 behaves strangely with "text-align: center;" in
# stylesheet, so use align="center" instead.
thumbnails_frame_entry_template = '''<a name="%(number)s"></a>
<a href="%(htmlref)s" class="toc" target="main">
<div align="center">
<img src="%(thumbimgref)s" class="toc" /></div>
</a>
'''

subalbum_entry_template = '''<td align="center" valign="top">
<p>%(title)s</p>
<table border="0" cellspacing="0" cellpadding="0">
<tr>
<td><img src="%(iconsdir)s/frame-topleft.png" /></td>
<td><img src="%(iconsdir)s/frame-top.png" width="6" height="6" /></td>
<td><img src="%(iconsdir)s/frame-top.png" width="%(thumbwidth_minus_6)s" height="6" /></td>
<td><img src="%(iconsdir)s/frame-toprightupper.png" /></td>
</tr>
<tr>
<td rowspan="2"><img src="%(iconsdir)s/frame-left.png" width="6" height="%(thumbheight)s" /></td>
<td rowspan="2" colspan="2"><a href="%(htmlref)s"><img src="%(thumbimgref)s" width="%(thumbwidth)s" height="%(thumbheight)s"/></a></td>
<td><img src="%(iconsdir)s/frame-toprightlower.png" /></td>
</tr>
<tr><td><img src="%(iconsdir)s/frame-right.png" width="17" height="%(thumbheight_minus_6)s" /></td></tr>
<tr>
<td colspan="2"><img src="%(iconsdir)s/frame-bottomleft.png" /></td>
<td><img src="%(iconsdir)s/frame-bottom.png" width="%(thumbwidth_minus_6)s" height="17" /></td>
<td><img src="%(iconsdir)s/frame-bottomright.png" /></td>
</tr>
</table>
</td>
'''

image_entry_template = '''<td align="left" valign="bottom">
<a href="%(frameref)s">
<img class="thinborder" src="%(thumbimgref)s" />
</a>
</td>
'''

image_frameset_template = '''<?xml version="1.0" encoding="%(charenc)s"?>
<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=%(charenc)s" />
<link rel="stylesheet" href="../woolly.css" type="text/css" />
<title>%(albumtitle)s</title>
</head>
<frameset cols="100%%, %(thumbnailsframesize)s">
<frame name="main" src="%(imageframeref)s" />
<frame name="toc" src="%(thumbnailsframeref)s#%(imagenumber)s" marginheight="20" />
<noframes>
This album needs frames. Sorry.
</noframes>
</frameset>
</html>
'''

image_frame_template = '''<?xml version="1.0" encoding="%(charenc)s"?>
<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=%(charenc)s" />
<link href="../woolly.css" type="text/css" rel="stylesheet" />
<title>%(title)s</title>
</head>
<body>
<table cellpadding="3" width="85%%" align="center" cellspacing="0">
<tr><td class="header">%(paths)s</td></tr>
<tr>
<td>

<table width="100%%">
<tr>
<td></td>
<td align="left">
<table>
<tr>
<td>%(previous)s</td>
<td>%(next)s</td>
<td><img src="%(iconsdir)s/1x1.png" height="1" width="20"></td>
<td>%(smaller)s</td>
<td>%(larger)s</td>
</tr>
</table>
</td>
<td></td>
</tr>
<tr>
<td></td>
<td><img src="%(iconsdir)s/1x1.png" height="1" width="%(imgmaxwidth)s" /></td>
<td></td>
</tr>
<tr>
<td width="50%%"></td>
<td align="center"><img class="thinborder" src="%(imgref)s" align="center" /></td>
<td width="50%%"></td>
</tr>
<tr><td></td><td class="info">%(info)s</td><td></td></tr>
<tr>
<td></td>
<td class="footer">
<p>&nbsp;</p>
<hr>
<small>%(blurb)s Image ID: %(imgid)s.</small>
</td>
<td></td>
</tr>
</table>

</td>
</tr>
</table>
</body>
</html>
'''


class OutputGenerator(OutputEngine):
    def __init__(self, env, character_encoding):
        OutputEngine.__init__(self, env)
        self.env = env
        self.charEnc = character_encoding
        if env.config.has_option("woolly", "display_categories"):
            displayCategories = re.split(r"(?:,|\s)\s*", env.config.get(
                "woolly",
                "display_categories"))
            self.displayCategories = [env.shelf.getCategory(x)
                                      for x in displayCategories
                                      if x]
        else:
            self.displayCategories = []
        self.autoImageDescTemplate = ""
        try:
            if env.config.getboolean("woolly", "enable_auto_descriptions"):
                tmpl = env.config.get("woolly", "auto_descriptions_template")
                self.autoImageDescTags = re.findall("<(.*?)>", tmpl)
                self.autoImageDescTemplate = re.sub(
                    "<(.*?)>", r"%(\1)s", tmpl).encode(self.charEnc)
        except ValueError:
            pass


    def preGeneration(self, root):
        self.iconsdir = "@icons"
        os.mkdir(os.path.join(self.dest, self.iconsdir))
        

    def postGeneration(self, root):
        if self.env.verbose:
            self.env.out("Generating index page, style sheet and icons...\n")
        self.symlinkFile(
            "%s.html" % root.getTag().encode(self.charEnc),
            "index.html")
        self.writeFile("woolly.css", css)
        for data, filename in [
                (transparent_1x1_png, "1x1.png"),
                (previous_png, "previous.png"),
                (noprevious_png, "noprevious.png"),
                (next_png, "next.png"),
                (nonext_png, "nonext.png"),
                (smaller_png, "smaller.png"),
                (nosmaller_png, "nosmaller.png"),
                (larger_png, "larger.png"),
                (nolarger_png, "nolarger.png"),
                (frame_bottom_png, "frame-bottom.png"),
                (frame_bottomleft_png, "frame-bottomleft.png"),
                (frame_bottomright_png, "frame-bottomright.png"),
                (frame_left_png, "frame-left.png"),
                (frame_right_png, "frame-right.png"),
                (frame_top_png, "frame-top.png"),
                (frame_topleft_png, "frame-topleft.png"),
                (frame_toprightlower_png, "frame-toprightlower.png"),
                (frame_toprightupper_png, "frame-toprightupper.png")]:
            self.writeFile(
                os.path.join(self.iconsdir, filename), data, 1)


    def generateAlbum(self, album, subalbums, images, paths):
        # ------------------------------------------------------------
        # Create album overview pages, one per size.
        # ------------------------------------------------------------

        self.makeDirectory(str(album.getId()))
        for size in self.env.imagesizes:
            # Create path text, used in top of the album overview.
            pathtextElements = []
            for path in paths:
                els = []
                for node in path:
                    title = node.getAttribute(u"title") or u""
                    els.append('''<a href="%(htmlref)s">%(title)s</a>''' % {
                        "htmlref": "%s-%s.html" % (
                            node.getTag().encode(self.charEnc),
                            size),
                        "title": title.encode(self.charEnc),
                        })
                pathtextElements.append(
                    u" \xbb ".encode(self.charEnc).join(els))
            pathtext = "<br />\n".join(pathtextElements)

            # Create text for subalbum entries.
            if subalbums:
                number = 0
                subalbumtextElements = ["<tr>\n"]
                for subalbum in subalbums:
                    if number % 3 == 0:
                        subalbumtextElements.append("</tr>\n<tr>\n")

                    frontimage = self._getFrontImage(subalbum)
                    if frontimage:
                        thumbimgref = self.getImageReference(
                            frontimage, self.env.thumbnailsize)
                        thumbwidth, thumbheight = self.getLimitedSize(
                            frontimage, self.env.thumbnailsize)
                    else:
                        thumbimgref = "%s/%s" % (self.iconsdir, "1x1.png")
                        thumbwidth = self.env.thumbnailsize
                        thumbheight = 3 * self.env.thumbnailsize / 4

                    title = subalbum.getAttribute(u"title") or u""
                    subalbumtextElements.append(subalbum_entry_template % {
                        "iconsdir": self.iconsdir,
                        "htmlref": "%s-%d.html" % (
                            subalbum.getTag().encode(self.charEnc),
                            size),
                        "thumbheight": thumbheight,
                        "thumbheight_minus_6": thumbheight - 6,
                        "thumbwidth": thumbwidth,
                        "thumbwidth_minus_6": thumbwidth - 6,
                        "thumbimgref": thumbimgref,
                        "title": title.encode(self.charEnc),
                        })
                    number += 1
                subalbumtextElements.append("</tr>\n")
                subalbumtext = "".join(subalbumtextElements)
            else:
                subalbumtext = ""

            # Create text for image entries.
            if images:
                number = 0
                imagetextElements = ["<tr>\n"]
                for image in images:
                    if number % 3 == 0:
                        imagetextElements.append("</tr>\n<tr>\n")
                    imagetextElements.append(image_entry_template % {
                        "frameref": "%s/%s-%s-frame.html" % (album.getId(),
                                                             number,
                                                             size),
                        "thumbimgref": self.getImageReference(
                            image,
                            self.env.thumbnailsize),
                        })
                    number += 1
                imagetextElements.append("</tr>\n")
                imagetext = "".join(imagetextElements)
            else:
                imagetext = ""

            # Album overview.
            desc = (album.getAttribute(u"description") or
                    album.getAttribute(u"title") or
                    u"")
            desc = desc.encode(self.charEnc)
            title = album.getAttribute(u"title") or u""
            title = title.encode(self.charEnc)

            self.writeFile(
                "%s-%s.html" % (album.getTag().encode(self.charEnc), size),
                album_template % {
                    "blurb": self.blurb,
                    "charenc": self.charEnc,
                    "description": desc,
                    "imageentries": imagetext,
                    "paths": pathtext,
                    "subalbumentries": subalbumtext,
                    "title": title,
                })
            self._maybeMakeUTF8Symlink("%s-%s.html" % (album.getTag(), size))

        # ------------------------------------------------------------
        # Create image thumbnails frame, one per size.
        # ------------------------------------------------------------

        for size in self.env.imagesizes:
            # Create text for image thumbnails frame.
            thumbnailsframeElements = []
            number = 0
            for image in images:
                thumbnailsframeElements.append(
                    thumbnails_frame_entry_template % {
                        "htmlref": "%s-%s.html" % (
                            number,
                            size),
                        "number": number,
                        "thumbimgref": "../" + self.getImageReference(
                            image,
                            self.env.thumbnailsize),
                        })
                number += 1
            thumbnailstext = "\n".join(thumbnailsframeElements)

            # Image thumbnails frame.
            self.writeFile(
                os.path.join(str(album.getId()), "thumbnails-%s.html" % size),
                thumbnails_frame_template % {
                    "charenc": self.charEnc,
                    "entries": thumbnailstext})
            self._maybeMakeUTF8Symlink(
                os.path.join(str(album.getId()), "thumbnails-%s.html" % size))

        # ------------------------------------------------------------
        # Create album symlink to default size.
        # ------------------------------------------------------------

        self.symlinkFile(
            "%s-%s.html" % (album.getTag().encode(self.charEnc),
                            self.env.defaultsize),
            "%s.html" % album.getTag().encode(self.charEnc))
        self._maybeMakeUTF8Symlink("%s.html" % album.getTag())


    def generateImage(self, album, image, images, number, paths):
        # ------------------------------------------------------------
        # Create image frameset, one per size.
        # ------------------------------------------------------------

        for size in self.env.imagesizes:
            title = album.getAttribute(u"title") or u""
            self.writeFile(
                os.path.join(str(album.getId()),
                             "%s-%s-frame.html" % (number, size)),
                image_frameset_template % {
                    "albumtitle": title.encode(self.charEnc),
                    "charenc": self.charEnc,
                    "imageframeref": "%s-%s.html" % (
                        number,
                        size),
                    "imagenumber": number,
                    "thumbnailsframeref": "thumbnails-%s.html" % size,
                    "thumbnailsframesize": self.env.thumbnailsize + 70,
                    })

        # ------------------------------------------------------------
        # Create image frame, one per size.
        # ------------------------------------------------------------

        for sizenumber in range(len(self.env.imagesizes)):
            size = self.env.imagesizes[sizenumber]

            # Create path text, used in top of the image frame.
            pathtextElements = []
            for path in paths:
                els = []
                for node in path:
                    title = node.getAttribute(u"title") or u""
                    els.append('''<a href="%(htmlref)s" target="_top">%(title)s</a>''' % {
                        "htmlref": "%s-%s.html" % (
                            node.getTag().encode(self.charEnc),
                            size),
                        "title": title.encode(self.charEnc),
                        })
                pathtextElements.append(
                    u" \xbb ".encode(self.charEnc).join(els))
            pathtext = "<br />\n".join(pathtextElements)

            if number > 0:
                previoustext = '<a href="%s"><img class="icon" src="../%s/previous.png" /></a>' % (
                    "%s-%s.html" % (number - 1, size),
                    self.iconsdir)
            else:
                previoustext = '<img class="icon" src="../%s/noprevious.png" />' % self.iconsdir

            if number < len(images) - 1:
                nexttext = '<a href="%s"><img class="icon" src="../%s/next.png" /></a>' % (
                    "%s-%s.html" % (number + 1, size),
                    self.iconsdir)
            else:
                nexttext = '<img class="icon" src="../%s/nonext.png" />' % self.iconsdir

            if sizenumber > 0:
                smallertext = '<a href="%s" target="_top"><img class="icon" src="../%s/smaller.png" /></a>' % (
                    "%s-%s-frame.html" % (
                        number, self.env.imagesizes[sizenumber - 1]),
                    self.iconsdir)

            else:
                smallertext = '<img class="icon" src="../%s/nosmaller.png" />' % self.iconsdir

            if sizenumber < len(self.env.imagesizes) - 1:
                largertext = '<a href="%s" target="_top"><img class="icon" src="../%s/larger.png" /></a>' % (
                    "%s-%s-frame.html" % (
                        number, self.env.imagesizes[sizenumber + 1]),
                    self.iconsdir)
            else:
                largertext = '<img class="icon" src="../%s/nolarger.png" />' % self.iconsdir

            desc = (image.getAttribute(u"description") or
                    image.getAttribute(u"title") or
                    u"")
            desc = desc.encode(self.charEnc)
            title = image.getAttribute(u"title") or u""
            title = title.encode(self.charEnc)

            imageCategories = list(image.getCategories())
            infotextElements = []
            if desc:
                descElement = desc
            else:
                if self.autoImageDescTemplate:
                    catdict = {}
                    for tag in self.autoImageDescTags:
                        catlist = []
                        cat = self.env.shelf.getCategory(tag)
                        for imgcat in imageCategories:
                            if cat.isParentOf(imgcat, True):
                                catlist.append(imgcat)
                        catdict[tag] = ", ".join(
                            [x.getDescription().encode(self.charEnc)
                             for x in catlist])
                    descElement = self.autoImageDescTemplate % catdict
                else:
                    descElement = ""
            infotextElements.append("<p>%s</p>\n" % descElement)
            infotextElements.append('<table border="0" cellpadding="0" cellspacing="0" width="100%">\n<tr>')
            firstrow = True
            for dispcat in self.displayCategories:
                matching = [x.getDescription().encode(self.charEnc)
                            for x in imageCategories
                            if dispcat.isParentOf(x, True)]
                if matching:
                    if firstrow:
                        firstrow = False
                    else:
                        infotextElements.append("<td></td></tr>\n<tr>")
                    infotextElements.append(
                        '<td align="left"><small><b>%s</b>: %s</small></td>' % (
                            dispcat.getDescription().encode(self.charEnc),
                            ", ".join(matching)))
            infotextElements.append('</td><td align="right">')
            timestamp = image.getAttribute(u"captured")
            if timestamp:
                infotextElements.append(
                    "<small>%s</small><br />" % (
                    timestamp.encode(self.charEnc)))
            infotextElements.append("</td></tr></table>")
            infotext = "".join(infotextElements)

            self.writeFile(
                os.path.join(str(album.getId()),
                             "%s-%s.html" % (number, size)),
                image_frame_template % {
                    "blurb": self.blurb,
                    "charenc": self.charEnc,
                    "iconsdir": "../" + self.iconsdir,
                    "imgid": image.getId(),
                    "imgmaxwidth": size,
                    "imgref": "../" + self.getImageReference(image, size),
                    "info": infotext,
                    "larger": largertext,
                    "next": nexttext,
                    "paths": pathtext,
                    "previous": previoustext,
                    "smaller": smallertext,
                    "title": title,
                    })


    def _getFrontImage(self, object, visited=None):
        if visited and object.getId() in visited:
            return None

        if object.isAlbum():
            if not visited:
                visited = []
            visited.append(object.getId())
            thumbid = object.getAttribute(u"frontimage")
            if thumbid:
                from kofoto.shelf import ImageDoesNotExistError
                try:
                    return self.env.shelf.getImage(thumbid)
                except ImageDoesNotExistError:
                    pass
            children = object.getChildren()
            try:
                return self._getFrontImage(children.next(), visited)
            except StopIteration:
                return None
        else:
            return object


    def _maybeMakeUTF8Symlink(self, filename):
        try:
            # Check whether the filename contains ASCII characters
            # only. If so, do nothing.
            filename.encode("ascii")
        except UnicodeError:
            if filename.encode(self.charEnc) != filename.encode("utf-8"):
                self.symlinkFile(
                    os.path.basename(filename.encode(self.charEnc)),
                    filename.encode("utf-8"))
