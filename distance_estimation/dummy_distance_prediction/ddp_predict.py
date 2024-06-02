import json
from argparse import ArgumentParser
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from PIL import Image
from ultralytics import YOLO

from distance_estimation.detection.predict import Detection, load_yolo_model, predict_detection
from distance_estimation.distance_prediction.helpers import DistanceDetection, draw_dist_detection_bbox
from distance_estimation.dummy_distance_prediction.ddp_prepare import get_focal_length


class DummyDistancePredictor:

    def __init__(self, model: Dict[str, float]):
        self.model = model

    def predict(self, detection: Detection, focal_length: float) -> DistanceDetection:
        class_idx = detection.class_idx.item()
        real_height = self.model[str(class_idx)]
        pixel_height = (detection.xyxy[3] - detection.xyxy[1]).item()
        distance = focal_length * real_height / pixel_height
        return DistanceDetection(**asdict(detection), distance=distance)

    @classmethod
    def load(cls, model_path: Path) -> "DummyDistancePredictor":
        model = json.load(open(model_path, "rb"))
        return cls(model=model)


def predict_dummy_distance_prediction(
    ddp_model: DummyDistancePredictor, yolo_model: YOLO, model_inp: Image.Image, focal_length: float
) -> List[DistanceDetection]:
    detections: List[Detection] = predict_detection(model=yolo_model, model_inp=model_inp)
    distance_detections = [ddp_model.predict(detection=detection, focal_length=focal_length) for detection in detections]
    return distance_detections


def main(args):
    yolo_model = load_yolo_model(model_path=args.detection_model_path)
    ddp_model = DummyDistancePredictor.load(model_path=args.ddp_model_path)
    print("Models loaded...")

    image = Image.open(args.img_path)
    focal_length: float = get_focal_length(img_path=args.img_path)

    detections: List[DistanceDetection] = predict_dummy_distance_prediction(
        ddp_model=ddp_model, yolo_model=yolo_model, model_inp=image, focal_length=focal_length
    )
    print("Detections performed...")

    print("Detections:", detections)
    if args.out_path:
        img = draw_dist_detection_bbox(image=image, detections=detections)
        img.save(args.out_path)
        print(f"Saved to file: {args.out_path}")


if __name__ == "__main__":
    parser = ArgumentParser("Detection predictor")
    parser.add_argument("-detmp", "--detection-model-path", type=str, required=True, help="YOLO model .pt file path")
    parser.add_argument("-ddpmp", "--ddp-model-path", type=str, required=True, help="model.json file path")
    parser.add_argument("-ip", "--img-path", type=str, required=True, help=".png file path")
    parser.add_argument("-op", "--out-path", type=str, required=False, help=".png file path")
    args = parser.parse_args()
    main(args)
