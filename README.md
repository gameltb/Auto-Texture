# Auto Texture

一个 blender 中使用 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 为后端的贴图 绘制/投射 辅助小插件.

# 插件会修改合成, 应当在一个新建的常规文件中打开, 避免影响你的工程.

# 使用步骤

1. 在本地启动 ComfyUI
2. 将当前相机对准要绘制贴图的物体, 并选中它, 注意: 直到完成投射之后, 才能修改这个相机的位置和方向
3. 点击插件中的渲染, 完成后 你应当可以在 ComfyUI 的 Load Image 节点找到 [ComfyUI 中的图片](#comfyui-中的图片)
4. 在 ComfyUI 中载入项目下的 workflow.json,你可以随意调整工作流,直到获得满意的图片.
5. [投射图片](#投射图片)
6. 重复 2-5 直到获得满意的贴图

## 渲染

此操作将修改合成与渲染参数,它将以当前相机视角渲染深度图和漫反射,并将 png 文件上传至本地的 ComfyUI, 在 ComfyUI 载入项目下的 workflow.json 可以看见默认工作流,你可以随意调整工作流,直到获得满意的图片.

### ComfyUI 中的图片

#### auto_tex_no_mask_depth.png

这是物体当前相机下的深度图片

#### auto_tex_mask_albedo.png

这是物体当前相机下的漫反射图片, 透明通道为投射区域蒙版

## 投射图片

在 ComfyUI 获得满意的图片后,右键打开图片,复制图片网址粘贴到 blender 中插件面版的 图片地址 里, 选中要投射的网格, 点击投射图片,会将网址内的图片以当前相机视角投射到模型的贴图上.

### Blender 中的图片

#### auto_tex_albedo_tex_ + 网格名称

这是插件生成和投射的漫反射贴图

#### auto_tex_albedo_mask_tex_ + 网格名称

这是插件投射的漫反射贴图蒙版, 白色为已投射部分, 影响渲染后的漫反射透明通道, 在 ComfyUI 中可以用来区分已绘制部分用于 Inpainting, 对于不满意的地方,可以涂成黑色,这样可以在 ComfyUI 中重绘.

此插件使用了一些来自 https://github.com/panmari/stanford-shapenet-renderer 的代码
