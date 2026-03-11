import{Config} from "./config.js"
import{Editor} from "./editor.js"
import {Data} from './data.js'


let pointsGlobalConfig = new Config();
window.pointsGlobalConfig = pointsGlobalConfig;


pointsGlobalConfig.load();


document.documentElement.className="theme-"+pointsGlobalConfig.theme;


document.body.addEventListener('keydown', event => {
    if (event.ctrlKey && 'asdv'.indexOf(event.key) !== -1) {
      event.preventDefault()
    }
});

async function createMainEditor(){

  let template = document.querySelector('#editor-template');
  let maindiv  = document.querySelector("#main-editor");
  let main_ui = template.content.cloneNode(true);
  maindiv.appendChild(main_ui); // input parameter is changed after `append`

  let editorCfg = pointsGlobalConfig;

  let dataCfg = pointsGlobalConfig;
  
  let data = new Data(dataCfg);
  await data.init();

  let editor = new Editor(maindiv.lastElementChild, maindiv, editorCfg, data, "main-editor")
  window.editor = editor;
  editor.run();
  return editor;
} 

async function start(){

  let mainEditor = await createMainEditor();

  let url = new URL(window.location.href);
  let dataset = url.searchParams.get("dataset") || url.searchParams.get("scene");
  let frame = url.searchParams.get("frame");

  if (!dataset){
    return;
  }

  if (!Object.prototype.hasOwnProperty.call(mainEditor.data.sceneDescList, dataset)){
    console.error(`dataset not found: ${dataset}`);
    return;
  }

  await mainEditor.scene_changed(dataset);

  let meta = mainEditor.data.getMetaBySceneName(dataset);
  if (!meta || !meta.frames || meta.frames.length === 0){
    console.error(`dataset has no frames: ${dataset}`);
    return;
  }

  let targetFrame = frame;
  if (!targetFrame || !meta.frames.includes(targetFrame)){
    targetFrame = meta.frames[0];
  }

  mainEditor.editorUi.querySelector("#scene-selector").value = dataset;
  mainEditor.editorUi.querySelector("#frame-selector").value = targetFrame;
  mainEditor.load_world(dataset, targetFrame);
}




start();
