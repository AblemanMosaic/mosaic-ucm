import {defineMosaicUI} from "@mosaic-ui/web";

export function createMosaicVueBinding(Vue, tagName = "mosaic-ui") {
  defineMosaicUI(tagName);
  return Vue.defineComponent({
    name: "MosaicUI",
    inheritAttrs: false,
    props: {
      endpoint: {type: String, required: true},
      width: {type: Number, default: 1280},
      height: {type: Number, default: 800},
      title: {type: String, default: "Mosaic UI"},
    },
    setup(props, context) {
      return () => Vue.h(tagName, {...context.attrs, ...props});
    },
  });
}
