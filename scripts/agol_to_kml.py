
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_URL = (
    "https://services9.arcgis.com/luQA2K3grtQZ8xXt/"
    "arcgis/rest/services/Lumet%C3%B5rje_26_27_WFL1/"
    "FeatureServer/10/query"
)

NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", NS)


def tag(name):
    return f"{{{NS}}}{name}"


def get_features():
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

        with urllib.request.urlopen(
            BASE_URL + "?" + params, timeout=60
        ) as response:
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


def main():
    features = get_features()
    if not features:
        raise RuntimeError("Keila 1 kihis puuduvad teelõigud")

    root = ET.Element(tag("kml"))
    document = ET.SubElement(root, tag("Document"))
    ET.SubElement(document, tag("name")).text = "Keila 1"

    style = ET.SubElement(document, tag("Style"), id="road")
    line_style = ET.SubElement(style, tag("LineStyle"))
    ET.SubElement(line_style, tag("color")).text = "ff00ffff"
    ET.SubElement(line_style, tag("width")).text = "3"

    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}

        placemark = ET.SubElement(document, tag("Placemark"))
        ET.SubElement(placemark, tag("name")).text = str(
            properties.get("tee_nimi") or "Nimetu tee"
        )
        ET.SubElement(placemark, tag("styleUrl")).text = "#road"

        extended = ET.SubElement(placemark, tag("ExtendedData"))
        for key in ("tee_number", "tsoon", "tootavja", "tootaja"):
            if properties.get(key) is not None:
                item = ET.SubElement(extended, tag("Data"), name=key)
                ET.SubElement(item, tag("value")).text = str(properties[key])

        if geometry.get("type") == "LineString":
            add_line(placemark, geometry["coordinates"])
        elif geometry.get("type") == "MultiLineString":
            multi = ET.SubElement(placemark, tag("MultiGeometry"))
            for coordinates in geometry["coordinates"]:
                add_line(multi, coordinates)

    ET.ElementTree(root).write(
        "keila1.kml",
        encoding="utf-8",
        xml_declaration=True
    )
    print(f"Valmis: keila1.kml ({len(features)} teelõiku)")


if __name__ == "__main__":
    main()
