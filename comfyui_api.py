import json
import os
import requests
import tempfile
import shutil

auto_tex_no_mask_depth_name = "auto_tex_no_mask_depth.png"
auto_tex_mask_albedo_name = "auto_tex_mask_albedo.png"

def queue_prompt(prompt):
    response = requests.post("http://127.0.0.1:8188/prompt", json=prompt)
    return response


def upload_tex(tex_name, tex_path):
    files = [('image', (tex_name, open(tex_path, 'rb'), 'image/png')),]
    response = requests.post("http://127.0.0.1:8188/upload/image", data={"overwrite": "1"}, files=files)
    return response


def do_rander(auto_tex_no_mask_depth_path=None, auto_tex_mask_albedo_path=None):
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.json")
    with open(prompt_path, "r") as f:
        prompt = json.load(f)

    if auto_tex_no_mask_depth_path != None:
        upload_tex(auto_tex_no_mask_depth_name, auto_tex_no_mask_depth_path)
    if auto_tex_mask_albedo_path != None:
        upload_tex(auto_tex_mask_albedo_name, auto_tex_mask_albedo_path)

    # queue_prompt(prompt)


def download_file(url, path):
    print("Downloading file from: " + url)
    r = requests.get(url, stream=True)
    if not r.ok:
        print("Get error code: " + str(r.status_code))
        print(r.text)
        return

    with open(os.path.realpath(path), 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    print("File downloaded to: " + path)


if __name__ == "__main__":
    # do_rander("/tmp/tmp/no_mask_depth0001.png","/tmp/tmp/mask_albedo0001.png")
    ...