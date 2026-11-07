import {defineMosaicUI} from "@mosaic-ui/web";

export function createMosaicReactBinding(React, tagName = "mosaic-ui") {
  defineMosaicUI(tagName);
  return function MosaicUI(props) {
    const {endpoint, width = 1280, height = 800, title = "Mosaic UI", ...rest} = props;
    return React.createElement(tagName, {endpoint, width, height, title, ...rest});
  };
}
