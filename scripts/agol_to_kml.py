
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SERVICE_URL = (
    "https://services9.arcgis.com/luQA2K3grtQZ8xXt/"
    "arcgis/rest/services/Lumet%C3%B5rje_26_27_WFL1/"
    "FeatureServer"
)

ZONES = {
    "keila1": (10, "Keila 1"),
    "keila2": (11, "Keila 2"),
    "keila3": (12, "Keila 3"),
    "vasalemma": (13, "Vasalemma"),
    "madise": (14, "Madise"),
    "paldiski": (15, "Paldiski"),
    "padise": (16, "Padise"),
}

NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", NS)


def tag(name):
    return f"{{{NS}}}{name}"


def get_features(layer_id):
    features = []
    offset = 0

    while True:
        params = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "*",
            "outSR": 4326,
            "returnGeometry": "true",
            "resultOffset": offset,
            "resultRecordCount": 500,
            "f": "geojson",
        })

        url = f"{SERVICE_URL}/{layer_id}/query?{params}"

        with urllib.request.urlopen(url, timeout=60) as response:
            data = json.load(response)

        if data.get("error"):
            raise RuntimeError(str(data["error"]))

        batch = data["features"]
        if not batch:
            break

        features.extend(batch)
        offset += len(batch)

        if len(batch) < 500:
            break

    return features


def add_line(parent, coordinates):
    line = ET.SubElement(parent, tag("LineString"))
    ET.SubElement(line, tag("tessellate")).text = "1"
    ET.SubElement(line, tag("coordinates")).text = " ".join(
        f"{point[0]},{point[1]},0"
        for point in coordinates
    )


def create_kml(filename, name, features):
    root = ET.Element(tag("kml"))
    document = ET.SubElement(root, tag("Document"))
    ET.SubElement(document, tag("name")).text = name

    style = ET.SubElement(document, tag("Style"), id="road")
    line_style = ET.SubElement(style, tag("LineStyle"))
    ET.SubElement(line_style, tag("color")).text = "ff00ffff"
    ET.SubElement(line_style, tag("width")).text = "3"

    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}

        geometry_type = geometry.get("type")
        if geometry_type not in ("LineString", "MultiLineString"):
            continue

        placemark = ET.SubElement(document, tag("Placemark"))

        ET.SubElement(placemark, tag("name")).text = str(
            properties.get("tee_nimi") or "Nimetu tee"
        )

        ET.SubElement(placemark, tag("styleUrl")).text = "#road"

        extended = ET.SubElement(placemark, tag("ExtendedData"))
        for key, value in properties.items():
            if value is not None:
                item = ET.SubElement(
                    extended, tag("Data"), name=str(key)
                )
                ET.SubElement(item, tag("value")).text = str(value)

        if geometry_type == "LineString":
            add_line(placemark, geometry["coordinates"])
        else:
            multi = ET.SubElement(placemark, tag("MultiGeometry"))
            for coordinates in geometry["coordinates"]:
                add_line(multi, coordinates)

    ET.ElementTree(root).write(
        filename,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"{filename}: {len(features)} teelõiku")


def main():
    # Kontrollime kõik tsoonid enne failide kirjutamist.
    all_features = {}

    for filename, (layer_id, name) in ZONES.items():
        print(f"Loen AGOL-ist: {name}")
        features = get_features(layer_id)

        if not features:
            raise RuntimeError(f"{name}: andmeid ei leitud")

        all_features[filename] = features

    for filename, (_, name) in ZONES.items():
        create_kml(
            f"{filename}.kml",
            name,
            all_features[filename]
        )

    print("Kõik 7 lumetõrje tsooni valmis!")


if __name__ == "__main__":
    main()
