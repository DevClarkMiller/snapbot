import os, json
from xml.etree.ElementTree import Element

from androidController import AndroidController

MAX_MENU_AGE = 150 # 2.5 minutes


class SnapchatController:
    def __init__(self, profileName):
        self.ctrl = AndroidController('snapchat', profileName)
        self.package = self.ctrl.appPackage('snapchat')
        self.ctrl.currPackage = self.package
        self.launchOption = self.ctrl.launcherActivity(self.package)

        # Close snapchat if possibly open
        self.ctrl.closePackage()
        self.ctrl.currPackage = ""

        # Open snapchat
        self.ctrl.openPackage(self.package, self.launchOption) # Opens app

        # On load, the current menu is home
        self.ctrl.menuChange("Home", 1800) # Lives for 30 minutes

        # Init the chats path
        self.chatsPath = f"{self.ctrl.profilePath}/chats"
        if not os.path.exists(self.chatsPath):
            os.makedirs(self.chatsPath)

    def openChatMenu(self):
        node = self.ctrl.findNode(lambda n: n.attrib.get("content-desc") == 'Chat')
        coords = self.ctrl.nodeCoords(node)

        self.ctrl.tap(coords)
        self.ctrl.menuChange('Chat', 60)

    # Fn: getUnopenedNodes()
    # Brief: Gets the nodes of all unopened messages
    # Rtns: A 2d array of the parent node, and the name and status node
    def getUnopenedNodes(self):
        chatNodes = self.ctrl.findNodes(lambda n: n.attrib.get('resource-id') == 'com.snapchat.android:id/ff_item')

        if len(chatNodes) > 0:
            # Get list of people to snap, ignore my ai
            chatNodes = chatNodes[1:]

        unopenedNodes = []

        for chatNode in chatNodes:
            nameNode = self.ctrl.findNode(lambda n: n.attrib.get('index') == '2', chatNode)
            statusNode = self.ctrl.findNode(lambda n: n.attrib.get('index') == '4', chatNode)
            if "New" in statusNode.attrib['text']:
                unopenedNodes.append([chatNode, nameNode, statusNode])

        return unopenedNodes

    # Fn: getChatHistory()
    # Brief: Checks for the json with the history, throws an error if one doesn't exist
    def getChatHistory(self, person):
        chatPath = f"{self.chatsPath}/{person}.json"
        if not os.path.exists(chatPath):
            raise Exception("Chat history doesn't exist")

        chatHist = None
        # Now just return the parsed json
        with open(chatPath, "r") as f:
            return json.load(f)

    # Fn: readConvo()
    # Brief: Reads in a convo from the start point, separates messages by the sender in order
    # Param: str - text, the text to parse
    # Param: set - people, the set of people
    def readConvo(self, text, people):
        res = []
        curr = ""
        for txt in text:
            if txt in people:
                curr = txt
                print(txt)
        return res

    # Fn: readWholeChat()
    # Brief: Scrolls the screen slowly to the top to read in the whole chat history
    def readWholeChat(self, person):
        scrnSize = self.ctrl.screenSize()
        snapController.ctrl.swipe((300, 250), (300, scrnSize[0]))
        # Just focus on reading in text here
        text = []

        # Now group the messages by their sender
        path = 'dump.xml'
        self.ctrl.dumpScreen(True, path)

        # preorder traversal of the xml document
        root = self.ctrl.root(path, False)

        def readIn():
            for node in root:
                if 'package' not in node.attrib:
                    continue
                if node.attrib['package'] == 'com.snapchat.android':
                    if 'text' in node.attrib:
                        txt = node.attrib['text']
                        if txt:
                            text.append(txt)

        readIn()
        res = []
        upperName = person.upper()
        # Now search for the first instance of a chat
        for i, txt in enumerate(text):
            if txt == 'ME' or txt == upperName:
                res = self.readConvo(text[i:], set([upperName]))

    # Fn: readChatMessages()
    # Brief: Opens the node corresponding to the person, and their messages and append to their history
    def getChatMessages(self, chatNode, person):
        # Firstly, fetch history and handle exception
        chatHist = None
        try:
            chatHist = self.getChatHistory(person)
        except Exception as e: # Means there is no history
            print(e)

        coords = self.ctrl.nodeCoords(chatNode)
        self.ctrl.tap(coords)
        self.ctrl.menuChange(f"Chat_{person}", 0) # Doesn't live at all, must be rescraped everytime

        chatList = []

        # Find the chat list
        chatListNode = self.ctrl.findNode(lambda n: n.attrib.get('resource-id') == 'com.snapchat.android:id/chat_message_list')

        # If it's a filtered keyword, skip. If it's a persons name, then append to current history until 'ME' is encountered
        upperName = person.upper()
        filterStrs = set(['TODAY', ''])  # Filtered words that won't be added to chat list

        hist = []
        currPersonMe = False
        for node in chatListNode:
            contentNode = node[0][0]
            textContent = contentNode.attrib.get("text")
            if textContent in filterStrs: # Just skip
                continue

            if textContent == "ME":
                currPersonMe = True
                if hist:
                    chatList.append([person, hist])
                    hist = []
            elif textContent == upperName:
                currPersonMe = False
                if hist:
                    chatList.append(["ME", hist])
                    hist = []
            else:
                hist.append(textContent)

if __name__ == "__main__":
    snapController = SnapchatController('satibot')
    snapController.openChatMenu()
    snapController.readWholeChat('Clark')
    # unopenedNodes = snapController.getUnopenedNodes()
    # if len(unopenedNodes) > 0:
    #     for parentNode, nameNode, statusNode in unopenedNodes:
    #         snapController.getChatMessages(parentNode, nameNode.attrib['text'])
