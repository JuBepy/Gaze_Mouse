import logging
import typing as T
import ndsi




from .observable import Observable

logger = logging.getLogger(__name__)


# _____ librairies additionnelles


from matplotlib import pyplot as plt
from PIL import Image
import cv2
import imutils
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


# __________ code d'initiation pour la détection de markers ______________________




# import the necessary packages
import argparse
import imutils
import cv2
import sys

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
# ap.add_argument("-i", "--image", required=True,
#     help="path to input image containing ArUCo tag")
ap.add_argument("-t", "--type", type=str,
    default="DICT_ARUCO_ORIGINAL",
    help="type of ArUCo tag to detect")
args = vars(ap.parse_args())

# define names of each possible ArUco tag OpenCV supports
ARUCO_DICT = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
    "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
#   "DICT_APRILTAG_16h5": cv2.aruco.DICT_APRILTAG_16h5,
#   "DICT_APRILTAG_25h9": cv2.aruco.DICT_APRILTAG_25h9,
#   "DICT_APRILTAG_36h10": cv2.aruco.DICT_APRILTAG_36h10,
#   "DICT_APRILTAG_36h11": cv2.aruco.DICT_APRILTAG_36h11
}

# load the input image from disk and resize it
# print("[INFO] loading image...")
# image = cv2.imread(args["image"])
# image = imutils.resize(image, width=600)

# verify that the supplied ArUCo tag exists and is supported by
# OpenCV
if ARUCO_DICT.get(args["type"], None) is None:
    print("[INFO] ArUCo tag of '{}' is not supported".format(
        args["type"]))
    sys.exit(0)

# load the ArUCo dictionary, grab the ArUCo parameters, and detect
# the markers
print("[INFO] detecting '{}' tags...".format(args["type"]))
arucoDict = cv2.aruco.Dictionary_get(ARUCO_DICT[args["type"]])
arucoParams = cv2.aruco.DetectorParameters_create()




#_________________ fin du code de détection de markers _________________________




class SortedHostDict(dict):
    def sorted_values(self) -> T.List["Host"]:
        return sorted(super().values(), key=lambda host: host.name)


class Host:
    def __init__(self, host_uuid, name):
        self.host_uuid = host_uuid
        self.name = name
        self.sensor_uuids = {}
        self.sensors = {}
        self.is_linked = False
        self.is_in_bad_state = False

    def __str__(self):
        return f"<{type(self).__name__} {self.name}>"

    @property
    def is_connected(self) -> bool:
        return any(self.sensors.values())

    @property
    def is_available(self) -> bool:
        return any(self.sensor_uuids.values())

    def add_sensor(self, network, sensor_type: str, sensor_uuid: str, sensor_name: str):
        if sensor_type == "video" and "world" not in sensor_name:
            return

        logger.debug(f"{self}.add_sensor({sensor_type})")
        self.sensor_uuids[sensor_type] = sensor_uuid

        if self.is_linked:
            self._connect_sensor(network, sensor_type)

    def remove_sensor(self, sensor_uuid_to_removed: str):
        logger.debug(f"{self}.remove_sensor({sensor_uuid_to_removed})")
        for sensor_type, sensor_uuid in self.sensor_uuids.copy().items():
            if sensor_uuid == sensor_uuid_to_removed:
                self._disconnect_sensor(sensor_type)
                del self.sensor_uuids[sensor_type]
                logger.debug(f"Detached: {sensor_type}")

    def poll_notifications(self):
        for sensor in self.sensors.values():
            while sensor.has_notifications:
                sensor.handle_notification()

    def fetch_recent_frame(self):
        if "video" in self.sensors:
            video_sensor = self.sensors["video"]
            try:
                frame = video_sensor.get_newest_data_frame(timeout=0) 
            except ndsi.StreamError:
                return
            return frame

    def fetch_recent_gaze(self):
        if "gaze" in self.sensors:
            gaze_sensor = self.sensors["gaze"]
            recent_gaze = None
            for x, y, ts in gaze_sensor.fetch_data():
                recent_gaze = x, y
            return recent_gaze

    def link(self, network):
        logger.debug(f"{self}.link()")
        self.is_linked = True
        for sensor_type in self.sensor_uuids:
            self._connect_sensor(network, sensor_type)

    def _connect_sensor(self, network, sensor_type):
        # disconnect existing sensor and replace
        self._disconnect_sensor(sensor_type)

        logger.debug(f"{self}._connect_sensor({sensor_type})")
        sensor_uuid = self.sensor_uuids[sensor_type]

        sensor = network.sensor(sensor_uuid)
        sensor.set_control_value("streaming", True)
        sensor.refresh_controls()
        self.sensors[sensor_type] = sensor

    def unlink(self):
        logger.debug(f"{self}.unlink()")
        for sensor_type in self.sensors.copy():
            self._disconnect_sensor(sensor_type)
        self.is_linked = False

    def _disconnect_sensor(self, sensor_type):
        logger.debug(f"{self}._disconnect_sensor({sensor_type})")
        try:
            sensor = self.sensors[sensor_type]
        except KeyError:
            return
        if sensor:
            sensor.unlink()
        del self.sensors[sensor_type]

    def cleanup(self):
        self.unlink()
        self.sensors.clear()


class Host_Controller(Observable):
    sensor_types = ("video", "gaze")

    def __init__(self):
        logger.info(f"Using NDSI protocol v{ndsi.__protocol_version__}")
        self._hosts = SortedHostDict()
        self.network = ndsi.Network(
            formats={ndsi.DataFormat.V4}, callbacks=(self.on_event,)
        )
        self.network.start()

    def __getitem__(self, idx: int):
        return self._hosts.sorted_values()[idx]

    def hosts(self):
        yield from self._hosts.sorted_values()

    def index(self, item: Host):
        return self._hosts.sorted_values().index(item)

    def cleanup(self):
        for host in self.hosts():
            host.cleanup()
        self.network.stop()

    def poll_events(self):
        while self.network.has_events:
            self.network.handle_event()

    def on_event(self, caller, event):
        if event["subject"] == "attach" and event["sensor_type"] in self.sensor_types:
            host_name = event["host_name"]
            if host_name not in self._hosts:
                host = Host(event["host_uuid"], host_name)
                self._hosts[host_name] = host
                host_idx = self.index(host)
                self.on_host_added(host_idx)

            host = self._hosts[host_name]
            host.add_sensor(
                self.network,
                event["sensor_type"],
                event["sensor_uuid"],
                event["sensor_name"],
            )
            host_idx = self.index(host)
            self.on_host_changed(host_idx)

        if event["subject"] == "detach" and event["host_name"] in self._hosts:
            host = self._hosts[event["host_name"]]
            host_idx = self.index(host)
            host.remove_sensor(event["sensor_uuid"])
            self.on_host_changed(host_idx)
            if not host.is_linked and not host.is_available:
                self.remove_host(event["host_name"])

    def link(self, host_to_connect_sensor):
        logger.debug(f"{type(self).__name__}.link({host_to_connect_sensor})")
        for host_idx, host in enumerate(self.hosts()):
            if host is host_to_connect_sensor and not host.is_linked:
                host.link(self.network)
                logger.info(f"Linked connected host {host}")
                self.on_host_changed(host_idx)
                self.on_host_linked()
            elif host is not host_to_connect_sensor and host.is_linked:
                host.unlink()
                logger.info(f"Unlinked previously connected host {host}")
                self.on_host_changed(host_idx)

        for host in self.hosts():
            if not host.is_linked and not host.is_available:
                self.remove_host(host.name)

    def remove_host(self, host_name):
        logger.debug(f"{type(self).__name__}.remove_host({host_name})")
        host = self._hosts[host_name]
        host_idx = self.index(host)
        del self._hosts[host_name]
        self.on_host_removed(host_idx)

    def fetch_recent_data(self):
        for idx, host in enumerate(self.hosts()):
            if host.is_linked:
                host.poll_notifications()
                try:
                    frame = host.fetch_recent_frame()
                    if frame is not None:
                        self.on_recent_frame(frame)

                        image = frame.bgr

                        # logger.warning(
                        #     f"Type test {type(test)} "
                        # )

                        # image = plt.imshow(img, interpolation='nearest')
                        # plt.show()
                        # plt.draw()
                        
                        

                        # image = Image.fromarray(img, 'RGB')
                        # logger.warning(type(image))
                        # # img.save('my.png')
                        # image.show()
                        # aruco(img)
                        image = imutils.resize(image, width=1000)

                    gaze = host.fetch_recent_gaze()
                    if gaze:
                        self.on_recent_gaze(gaze)
                        # print(f"Coordonnees absolues : {gaze}")    # Modif VDB
                    # else: #est ce qu'on peut considérer que si on a pas de gaze, on clique ?


                    # ____________ détection des markers et clic __________________

                    markerrrrss = {24 : 0, 42 : 0, 66 : 0, 70 : 0}
                    if gaze and frame:
                        (corners, ids, rejected) = cv2.aruco.detectMarkers(image, arucoDict,
                                                parameters=arucoParams)
                        if len(corners) > 3:        # si il y a plus de 3 markers, alors on peut faire le clic
                            # flatten the ArUco IDs list
                            ids = ids.flatten()

                            # loop over the detected ArUCo corners
                            for (markerCorner, markerID) in zip(corners, ids):
                                # extract the marker corners (which are always returned in
                                # top-left, top-right, bottom-right, and bottom-left order)
                                corners = markerCorner.reshape((4, 2))
                                (topLeft, topRight, bottomRight, bottomLeft) = corners

                                # convert each of the (x, y)-coordinate pairs to integers
                                # topRight = (int(topRight[0]), int(topRight[1]))
                                # bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
                                # bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
                                # topLeft = (int(topLeft[0]), int(topLeft[1]))

                                # print("[INFO] ArUco marker ID: {}".format(markerID))
                                # logger.warning(
                                #     f"[INFO] ArUco marker ID: {markerID} "
                                # )

                                # le rectange est composé des markers aux ID 42 en haut à droite, 24 en haut à gauche, ...
                                if markerID == 42:
                                    markerrrrss[markerID] = (int(topLeft[0]), int(topLeft[1]))
                                elif markerID == 24:
                                    markerrrrss[markerID] = (int(topRight[0]), int(topRight[1]))
                                elif markerID == 66:
                                    markerrrrss[markerID] = (int(bottomLeft[0]), int(bottomLeft[1]))
                                elif markerID == 70:
                                    markerrrrss[markerID] = (int(bottomRight[0]), int(bottomRight[1]))



                            # logger.warning(markerrrrss.keys())
                            # la création du polygone se fait en détectant les points dans le sens trigonométrique
                            # ici, on détecte sur l'utilisateur regarde dans le rectangle créé par les markers.
                            # la fonction polygon.contains permet d'inclure les transformations dûes à l'orientation des lunettes par rapports aux markers en 1 fonction
                            if Polygon([(markerrrrss[24][0], markerrrrss[24][1]), (markerrrrss[42][0], markerrrrss[42][1]), (markerrrrss[66][0], markerrrrss[66][1]), (markerrrrss[70][0], markerrrrss[70][1])]).contains(Point(gaze[0], gaze[1])):
                                logger.warning("Le gaze est compris dans le rectangle formé par les 4 markers")
                                width = markerrrrss[24][0] - markerrrrss[42][0]
                                height = markerrrrss[66][1] - markerrrrss[42][1]
                                relative_position_x = (gaze[0] - markerrrrss[42][0])/width
                                relative_position_y = (gaze[1] - markerrrrss[42][1])/height
                                screen_width = 1920
                                screen_height = 1080
                                mouse.move(relative_position_x * screen_width, relative_position_y * screen_height, absolute=True, duration=0)

                                #pour cliquer avec le clin d'oeil, il faut voir si ça existe dans les sensors : ceux-ci sont cités à la fin dans https://github.com/pupil-labs/pyndsi/blob/master/src/ndsi/sensor.py
                                # ça n'a pas l'air possible donc il faudrait sûrement le faire avec le gaze qui n'existerait pas avec un oeil fermé ? donc on ajouterait un else à if gaze
                            else 
                                logger.warning("Non, Le gaze n'est pas compris dans le rectangle formé par les 4 markers")

                            # ___________________ fin du code de détection des markers et clic _______________
                except ndsi.sensor.NotDataSubSupportedError:
                    logger.warning(
                        f"Host {host} is in bad state. "
                        "Please force-restart Pupil Invisible Companion."
                    )
                    self.is_in_bad_state = True
                    self.on_host_changed(idx)

    def on_host_added(self, host_idx):
        pass

    def on_host_removed(self, host_idx):
        pass

    def on_host_changed(self, host_idx):
        pass

    def on_recent_frame(self, frame):
        pass

    def on_recent_gaze(self, gaze):
        pass

    def on_host_linked(self):
        pass