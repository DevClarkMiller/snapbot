import os, subprocess
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from PIL import Image
import json
from phoneController import PhoneController

class AndroidController(PhoneController):
    def __init__(self, controllerName, profileName):
        # Print device details
        print(f"Battery Level: {self.battery()}%")
        self.currPackage = ""
        self.menu = ""
        self.menu_update_times = dict() # Each time a screen is pulled for a menu
        self.profilePath = f"screens/{controllerName}/{profileName}"

        # Init the screensdir, which is the directory of xml files correlating to apps, and their screens
        if not os.path.exists(self.profilePath):
            os.makedirs(self.profilePath)

        self.jsonPath = f"{self.profilePath}/menu_update_times.json"

        try:
            with open(self.jsonPath, "r+") as f:
                data = f.read()  # Read whole file into data
                self.menu_update_times = json.loads(data)
        except: # Means file doesn't exist
            f = open(self.jsonPath, 'w+')
            f.write(json.dumps(self.menu_update_times))
            f.close()

    def save(self):
        with open(self.jsonPath, 'w+') as f:
            data = json.dumps(self.menu_update_times)
            f.write(data)

    def command(self, cmd, isShell=True, captureOutput = True, text=False):
        if isShell:
            cmd = ['adb', 'shell'] + cmd
        else:
            cmd = ['adb'] + cmd

        result = None
        if captureOutput:
            result = subprocess.run(cmd, capture_output=True, text=text)
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout.decode("utf-8")

    def menuPath(self):
        return f"{self.profilePath}/{self.menu}.xml"

    def menuExpired(self):
        if not os.path.exists(self.menuPath()):
            return True

        if self.menu not in self.menu_update_times:
            return True

        start = self.menu_update_times[self.menu]["start"]
        ttl = self.menu_update_times[self.menu]["ttl"]
        return datetime.now().timestamp() - start > ttl

    def swipe(self, frm, to, duration = 500):
        cmd = ['input', 'swipe']

        nums = [frm[0], frm[1], to[0], to[1], duration]
        cmd += [str(num) for num in nums]
        self.command(cmd)

    def tap(self, coord):
        self.command(['input', 'tap', str(coord[0]), str(coord[1])])

    def screenSize(self):
        return list(map(int, (self.command(['wm', 'size'], text=True)[15:].split('x'))))

    def download(self, devicePath, clientPath):
        return self.command(['pull', devicePath, clientPath], text=True, isShell=False)

    def screenshot(self, filename):
        self.command(['screencap', '-p', '/sdcard/screenshot.png'])
        self.download('/sdcard/screenshot.png', filename)

    def battery(self):
        return self.command(['cat', '/sys/class/power_supply/battery/capacity'], text=True)

    def packages(self):
        return self.command(['pm', 'list', 'packages'], text=True).split('\n')

    def launcherActivity(self, package):
        res = self.command(
            ['cmd', 'package', 'resolve-activity', '--brief', package],
            text=True
        )
        activities = res.split('\n')[1:] # Ignore the first bad line

        # Just return the first
        if '/' in activities[0]:
            return activities[0].split('/')[1]
        else:
            return activities[0]

    def appPackage(self, app):
        packages = self.packages()
        app = app.strip().lower()

        for pkg in packages:
            if app in pkg.lower():
                return pkg.lower().split(":")[1]
        return None

    def openPackage(self, package, launchActivity):
        if self.currPackage != package:
            self.currPackage = package
            return self.command(["am", "start", "-n", f"{package}/{launchActivity}"], text=True)
        return None

    def closePackage(self):
        self.command(['am', 'force-stop', self.currPackage])

    # Fn: dumpScreen()
    # Brief: Dumps screen into xml if it hasn't been scraped recently / not at all
    # Param: Boolean - force: dump the screen without doing checks
    def dumpScreen(self, force = False, path = ""):
        dumping = force

        # Check age of the current menu
        if not force and self.menuExpired():
            dumping = True

        if path == '':
            path = self.menuPath()

        if dumping:
            self.command(["uiautomator", 'dump'])
            # Now pull this
            return self.download('/sdcard/window_dump.xml', path)

    # Fn: allScreenText()
    # Brief: Extracts all pieces of text from the scren
    def allScreenText(self, path = ""):
        if path == "":
            path = self.menuPath()

        self.dumpScreen(force=True, path=path)
        # Now get the root of the xml
        root = self.root(path)

    # Fn: menuChange()
    # Brief: Update the current menu, also scrapes the screen. These menu names are created by the coder
    # Param: str - menuName: The menu to be changed to
    # Param: number - ttl: The time until the menu expires and has to be refreshed
    def menuChange(self, menuName, ttl = 150):
        self.menu = menuName
        if self.menuExpired(): # Only refresh and scrape the menu if it's expired
            self.dumpScreen() # Dump screen on menu change
            self.menu_update_times[menuName] = {
                "start": datetime.now().timestamp(),
                "ttl": ttl
            }
            self.save() # Save if menu is expired

    # Fn: displayScreen()
    # Brief: Screenshots, then displays the screen with pillow
    def displayScreen(self, window_name = "TestScreen"):
        filename = f'{window_name}.png'
        self.screenshot(filename)
        im = Image.open(filename)
        im.show('Android Screen')

    # Fn: root()
    # Brief: Gets the root of the xml document
    def root(self, path = '', doDump = True):
        if path == '':
            path = self.menuPath()
        if doDump:
            self.dumpScreen()
        tree = ET.parse(path)
        return tree.getroot().findall('.//')

    # Fn: findNode()
    # Brief: Finds a node from a root given a predicate
    def findNode(self, predicate: callable, root = None) -> Element | None:
        if not root:
            root = self.root()
        return next((n for n in root if predicate(n)), None)

    # Fn: findNodes()
    # Brief: Finds multiple nodes from a root given a predicate
    def findNodes(self, predicate: callable, root = None):
        if not root:
            root = self.root()
        nodes = []
        for node in root:
            if predicate(node):
                nodes.append(node)
        return nodes

    # Fn: nodeCoords()
    # Brief: Returns the parsed coords of the node
    def nodeCoords(self, node):
        coords = node.attrib['bounds']
        crdsSplt = coords.split(']')
        frm = list(map(int, crdsSplt[0][1:].split(',')))
        to = list(map(int, crdsSplt[1][1:].split(',')))

        return [(frm[0] + to[0]) / 2, (frm[1] + to[1]) / 2]

    # Fn: findCoords()
    # Brief: Finds a node based off a lambda, then returns its coords
    def findCoords(self, predicate: callable):
        node = self.findNode(predicate)
        if node is None:
            return None
        return self.nodeCoords(node)