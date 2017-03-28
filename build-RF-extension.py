# [h] build hTools2 as a RoboFont Extension

import hTools2
reload(hTools2)

import os
from mojo.extensions import ExtensionBundle

hTools2_path = os.path.dirname(os.path.dirname(hTools2.__file__ ))
hTools2_html = os.path.join(os.path.dirname(hTools2_path), "Docs/build/html")

extension_file = 'hTools2.roboFontExt'
extension_path = os.path.join(os.path.dirname(__file__), extension_file)

print 'building extension...',

B = ExtensionBundle()
B.name = "hTools2"
B.developer = 'Gustavo Ferreira'
B.developerURL = 'http://hipertipo.com/'
B.version = "1.8"
B.mainScript = "init-RF-extension.py"
B.launchAtStartUp = 1
B.addToMenu = []
B.requiresVersionMajor = '1'
B.requiresVersionMinor = '5'
B.infoDictionary["repository"] = 'gferreira/hTools2'
B.infoDictionary["summary"] = 'A collection of tools to help with common type design & font production tasks.'
B.infoDictionary["html"] = 1
B.save(extension_path, libPath=hTools2_path, htmlPath=hTools2_html, resourcesPath=None, pycOnly=False)

print 'done.'
