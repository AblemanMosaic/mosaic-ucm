import {defineMosaicUI} from "@mosaic-ui/web";

export function mosaicUI(node, options = {}) {
  defineMosaicUI(options.tagName || "mosaic-ui");
  let element;
  function apply(value) {
    const next = value || {};
    const tagName = next.tagName || "mosaic-ui";
    if (!element || element.tagName.toLowerCase() !== tagName) {
      if (element) element.remove();
      element = document.createElement(tagName);
      node.appendChild(element);
    }
    for (const name of ["endpoint", "width", "height", "title"]) {
      if (next[name] == null) element.removeAttribute(name);
      else element.setAttribute(name, String(next[name]));
    }
  }
  apply(options);
  return {update: apply, destroy() { if (element) element.remove(); }};
}
