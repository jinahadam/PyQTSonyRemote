import rospy
import sys, json, time
import httplib
import threading
import base64, hashlib
import functools
import urllib

from urlparse import urlparse
from PyQt4.QtCore import *
from PyQt4.QtGui import *




lock = threading.Lock()

app = QApplication(sys.argv)
image = QImage()

class ImageDisplay(QLabel):
    def __init__(self):
        QLabel.__init__(self)

    def paintEvent(self, event):
        global lock
        lock.acquire()
        try:
            self.setPixmap(QPixmap.fromImage(image))
        finally:
            lock.release()
        QLabel.paintEvent(self, event)




pId = 0
headers = {"Content-type": "text/plain", "Accept": "*/*", "X-Requested-With": "com.sony.playmemories.mobile"}

AUTH_CONST_STRING = "90adc8515a40558968fe8318b5b023fdd48d3828a2dda8905f3b93a3cd8e58dc"
METHODS_TO_ENABLE = "camera/setFlashMode:camera/getFlashMode:camera/getSupportedFlashMode:camera/getAvailableFlashMode:camera/setExposureCompensation:camera/getExposureCompensation:camera/getSupportedExposureCompensation:camera/getAvailableExposureCompensation:camera/setSteadyMode:camera/getSteadyMode:camera/getSupportedSteadyMode:camera/getAvailableSteadyMode:camera/setViewAngle:camera/getViewAngle:camera/getSupportedViewAngle:camera/getAvailableViewAngle:camera/setMovieQuality:camera/getMovieQuality:camera/getSupportedMovieQuality:camera/getAvailableMovieQuality:camera/setFocusMode:camera/getFocusMode:camera/getSupportedFocusMode:camera/getAvailableFocusMode:camera/setStillSize:camera/getStillSize:camera/getSupportedStillSize:camera/getAvailableStillSize:camera/setBeepMode:camera/getBeepMode:camera/getSupportedBeepMode:camera/getAvailableBeepMode:camera/setCameraFunction:camera/getCameraFunction:camera/getSupportedCameraFunction:camera/getAvailableCameraFunction:camera/setLiveviewSize:camera/getLiveviewSize:camera/getSupportedLiveviewSize:camera/getAvailableLiveviewSize:camera/setTouchAFPosition:camera/getTouchAFPosition:camera/cancelTouchAFPosition:camera/setFNumber:camera/getFNumber:camera/getSupportedFNumber:camera/getAvailableFNumber:camera/setShutterSpeed:camera/getShutterSpeed:camera/getSupportedShutterSpeed:camera/getAvailableShutterSpeed:camera/setIsoSpeedRate:camera/getIsoSpeedRate:camera/getSupportedIsoSpeedRate:camera/getAvailableIsoSpeedRate:camera/setExposureMode:camera/getExposureMode:camera/getSupportedExposureMode:camera/getAvailableExposureMode:camera/setWhiteBalance:camera/getWhiteBalance:camera/getSupportedWhiteBalance:camera/getAvailableWhiteBalance:camera/setProgramShift:camera/getSupportedProgramShift:camera/getStorageInformation:camera/startLiveviewWithSize:camera/startIntervalStillRec:camera/stopIntervalStillRec:camera/actFormatStorage:system/setCurrentTime"

def postRequest(conn, target, req):
    global pId
    pId += 1
    req["id"] = pId
#    print("REQUEST  [%s]: " % target, end = "")
    print(req)
    conn.request("POST", "/sony/" + target, json.dumps(req), headers)
    response = conn.getresponse()
 #   print("RESPONSE [%s]: " % target, end = "")
    #print(response.status, response.reason)
    data = json.loads(response.read().decode("UTF-8"))
    print(data)
    if data["id"] != pId:
        print("FATAL ERROR: Response id does not match")
        return {}
    if "error" in data:
        print("WARNING: Response contains error code: %d; error message: [%s]" % tuple(data["error"]))
    print("")
    return data

def exitWithError(conn, message):
    print("ERROR: %s" % message)
    conn.close()
    sys.exit(1)

def parseUrl(url):
    parsedUrl = urlparse(url)
    return parsedUrl.hostname, parsedUrl.port, parsedUrl.path + "?" + parsedUrl.query, parsedUrl.path[1:]

def downloadImage(url):
    host, port, address, img_name = parseUrl(url)
    conn2 = httplib.HTTPConnection(host, port)
    conn2.request("GET", address)
    response = conn2.getresponse()
    if response.status == 200:
        with open(img_name, "wb") as img:
            img.write(response.read())
    else:
        print("ERROR: Could not download picture, error = [%d %s]" % (response.status, response.reason))

#def symb5(c):
#    s = str(c)
#    while len(s) < 5:
#        s = "0" + s
#    return s

def liveviewFromUrl(url):
    global image
    global lock
    host, port, address, img_name = parseUrl(url)
    conn3 = httplib.HTTPConnection(host, port)
    conn3.request("GET", address)
    response = conn3.getresponse()
    #flow = open("liveview", "wb")
    if response.status == 200:
        buf = b''
        c = 0
        while response.status == 200:
            nextPart = response.read(1024)
            #flow.write(nextPart)
            #flow.flush()

            # TODO: It would be better to use description from the documentation (page 51) for parsing liveview stream
            jpegStart = nextPart.find(b'\xFF\xD8\xFF')
            jpegEnd = nextPart.find(b'\xFF\xD9')
            if jpegEnd != -1:
                c += 1
                buf += nextPart[:jpegEnd + 2]
                #with open("live_" + symb5(c) + ".jpg", "wb") as liveImg:
                #    liveImg.write(buf)
                lock.acquire()
                try:
                    image.loadFromData(buf)
                finally:
                    lock.release()
            if jpegStart != -1:
                buf = nextPart[jpegStart:]
            else:
                buf += nextPart

def communicationThread():
    #target = "/sony/camera"
    #target = "/sony/system"
    #target = "/sony/accessControl"

    #req = {"method": "getVersions", "params": [], "id": 1}
    #req = {"method": "getApplicationInfo", "params": [], "id": 2, "version": "1.0"}
    #req = {"method": "getEvent", "params": [False], "id": 3, "version": "1.0"}        # (!!!) get method list
    #req = {"method": "getEvent", "params": [True], "id": 4, "version": "1.0"}
    #req = {"method": "getMethodTypes", "params": ["1.0"], "id": 8, "version": "1.0"}

    conn = httplib.HTTPConnection("10.0.0.1", 10000)

    resp = postRequest(conn, "camera", {"method": "getVersions", "params": []})
    if resp["result"][0][0] != "1.0":
        exitWithError(conn, "Unsupported version")

    resp = postRequest(conn, "accessControl", {"method": "actEnableMethods", "params": [{"methods": "", "developerName": "", "developerID": "", "sg": ""}], "version": "1.0"})
    dg = resp["result"][0]["dg"]

   # h = hashlib.sha256()
   # h.update(bytes(AUTH_CONST_STRING + dg, "UTF-8"))
   # sg = base64.b64encode(h.digest()).decode("UTF-8")

    # resp = postRequest(conn, "accessControl", {"method": "actEnableMethods", "params": [{"methods": METHODS_TO_ENABLE, "developerName": "Sony Corporation", "developerID": "7DED695E-75AC-4ea9-8A85-E5F8CA0AF2F3", "sg": sg}], "version": "1.0"})
    #
    # resp = postRequest(conn, "system", {"method": "getMethodTypes", "params": ["1.0"], "version": "1.0"})
    # resp = postRequest(conn, "accessControl", {"method": "getMethodTypes", "params": ["1.0"], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "getStillSize", "params": [], "version": "1.0"})
    # #resp = postRequest(conn, "camera", {"method": "getSupportedStillSize", "params": [], "version": "1.0"})
    #resp = postRequest(conn, "camera", {"method": "getAvailableStillSize", "params": [], "version": "1.0"})

    #resp = postRequest(conn, "camera", {"method": "setStillSize", "params": ["20M", "3:2"], "version": "1.0"})

    # resp = postRequest(conn, "camera", {"method": "setFocusMode", "params": ["AF-S"], "version": "1.0"})
    # resp = postRequest(conn, "camera", {"method": "getFocusMode", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "stopLiveview", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["Original"], "version": "1.0"})
    # while "error" in resp:
    #     resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["Original"], "version": "1.0"})
    # resp = postRequest(conn, "camera", {"method": "getPostviewImageSize", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "actTakePicture", "params": [], "version": "1.0"})
    # downloadImage(resp["result"][0][0])
    #
    # resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["2M"], "version": "1.0"})
    # while "error" in resp:
    #     resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["2M"], "version": "1.0"})
    # resp = postRequest(conn, "camera", {"method": "getPostviewImageSize", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "actTakePicture", "params": [], "version": "1.0"})
    # downloadImage(resp["result"][0][0])
    #
    # resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["Original"], "version": "1.0"})
    # while "error" in resp:
    #     resp = postRequest(conn, "camera", {"method": "setPostviewImageSize", "params": ["Original"], "version": "1.0"})
    # resp = postRequest(conn, "camera", {"method": "getPostviewImageSize", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "actTakePicture", "params": [], "version": "1.0"})
    # downloadImage(resp["result"][0][0])
    #
    # resp = postRequest(conn, "camera", {"method": "getAvailableFocusMode", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "getSupportedFocusMode", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "getTouchAFPosition", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "getSupportedFNumber", "params": [], "version": "1.0"})
    #
    # #resp = postRequest(conn, "camera", {"method": "setFocusMode", "params": ["MF"], "version": "1.0"})
    # #resp = postRequest(conn, "camera", {"method": "getFocusMode", "params": [], "version": "1.0"})
    #
    # resp = postRequest(conn, "camera", {"method": "getEvent", "params": [False], "version": "1.0"})

    resp = postRequest(conn, "camera", {"method": "startLiveview", "params": [], "version": "1.0"})
    liveview = threading.Thread(target = liveviewFromUrl, args = (resp["result"][0],))
    liveview.start()


#    conn.close()

class Form(QDialog):


    def __init__(self, parent=None):
        super(Form, self).__init__(parent)

        #camera functions
        takePicBtn = QPushButton("Take Picture")
        zoomInBtn = QPushButton("Zoom in")
        zoomOutBtn = QPushButton("Zoom out")
        self.FComboBox = QComboBox(self)
        self.ISOComboBox = QComboBox(self)
        self.ShutterComboBox = QComboBox(self)
        self.label = QLabel("Standing by..")

        #live stream
        imgDisplay = ImageDisplay()
        imgDisplay.setMinimumSize(640, 480)
        imgDisplay.show()

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(imgDisplay,2,0)

        controlLayout = QGridLayout()
        controlLayout.setSpacing(10)
        controlLayout.addWidget(zoomInBtn, 0, 0)
        controlLayout.addWidget(takePicBtn, 0, 1)
        controlLayout.addWidget(zoomOutBtn, 0, 2)
        controlLayout.addWidget(QLabel("Aperture"),2,0)
        controlLayout.addWidget(self.FComboBox,2,1)
        controlLayout.addWidget(QLabel("Shutter Speed"),3,0)
        controlLayout.addWidget(self.ShutterComboBox,3,1)
        controlLayout.addWidget(QLabel("ISO"),4,0)
        controlLayout.addWidget(self.ISOComboBox,4,1)
        controlLayout.addWidget(self.label,5,1)
        self.getSupportedExposureModes(grid)
        grid.addLayout(controlLayout,2,1)

        self.setLayout(grid)

        #conenections
        self.connect(takePicBtn, SIGNAL("clicked()"), self.takePic)
        self.connect(zoomInBtn, SIGNAL("pressed()"), self.zoomIn)
        self.connect(zoomInBtn, SIGNAL("released()"), self.zoomInStop)
        self.connect(zoomOutBtn, SIGNAL("pressed()"), self.zoomOut)
        self.connect(zoomOutBtn, SIGNAL("released()"), self.zoomOutStop)
        self.FComboBox.currentIndexChanged['QString'].connect(self.handleFChange)
        self.ISOComboBox.currentIndexChanged['QString'].connect(self.handleISOChange)
        self.ShutterComboBox.currentIndexChanged['QString'].connect(self.handleShutterChange)

        #camera controls
        self.getAvailableFNumber(grid)
        self.getAvailableIsoSpeedRate(grid)
        self.getAvailableShutterSpeed(grid)


    def getSupportedExposureModes(self, grid):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "getAvailableExposureMode", "params": [], "version": "1.0"})
        self.label.setText("Current Mode:" + resp["result"][0])
        available_modes = resp["result"][1]
        #available_modes = ['Intelligent Auto', 'Superior Auto', 'Program Auto', 'Aperture', 'Shutter']
        layout = QHBoxLayout()
        label = QLabel("Camera Modes:")
        layout.addWidget(label)
        for m in available_modes:
            b = QPushButton(m)
            self.connect(b, SIGNAL("clicked()"), functools.partial(self.setExposureMode, m, grid))
            layout.addWidget(b)
        layout.addStretch()
        grid.addLayout(layout,0,0)

    def setExposureMode(self, m, grid):
        self.label.setText("Setting Mode")
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "setExposureMode", "params": [m], "version": "1.0"})
        if resp["result"][0] == 0:
            self.clearCombo(self.ISOComboBox)
            self.clearCombo(self.FComboBox)
            self.clearCombo(self.ShutterComboBox)

            self.label.setText("New Mode Set:" + m)
            self.getAvailableFNumber(grid)
            self.getAvailableIsoSpeedRate(grid)
            self.getAvailableShutterSpeed(grid)

    def getAvailableFNumber(self, grid):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "getAvailableFNumber", "params": [], "version": "1.0"})
        try:
            available_modes = resp["result"][1]
            self.FComboBox.addItems(available_modes)
        except:
            pass

    def getAvailableIsoSpeedRate(self, grid):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "getAvailableIsoSpeedRate", "params": [], "version": "1.0"})
        try:
            available_modes = resp["result"][1]
            self.ISOComboBox.addItems(available_modes)
        except:
            pass

    def getAvailableShutterSpeed(self, grid):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "getAvailableShutterSpeed", "params": [], "version": "1.0"})
        try:
            available_modes = resp["result"][1]
            self.ShutterComboBox.addItems(available_modes)
        except:
            pass

    def takePic(self):
        self.label.setText("Capturing Image")
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "actTakePicture", "params": [], "version": "1.0"})
        downloadImage(resp["result"][0][0])

    def zoomIn(self):
        self.label.setText("Zoom In")
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "actZoom", "params": ["in", "start"], "version": "1.0"})

    def zoomInStop(self):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "actZoom", "params": ["in", "stop"], "version": "1.0"})


    def zoomOut(self):
        self.label.setText("Zoom In")
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "actZoom", "params": ["out", "start"], "version": "1.0"})

    def zoomOutStop(self):
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "actZoom", "params": ["out", "stop"], "version": "1.0"})



    def handleFChange(self, text):
        print('handleChanged: %s' % text)
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "setFNumber", "params": [text], "version": "1.0"})

    def handleISOChange(self, text):
        print('handleChanged: %s' % text)
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "setIsoSpeedRate", "params": [text], "version": "1.0"})

    def handleShutterChange(self, text):
        print('handleChanged: %s' % text)
        conn = httplib.HTTPConnection("10.0.0.1", 10000)
        resp = postRequest(conn, "camera", {"method": "setShutterSpeed", "params": [text], "version": "1.0"})

    def clearCombo(self,combo):
        for i in range(combo.count(),-1,-1):
                print(i)
                combo.removeItem(i)

form = Form()
form.show()



if __name__ == "__main__":
    communication = threading.Thread(target = communicationThread)
    communication.start()
    sys.exit(app.exec_())
