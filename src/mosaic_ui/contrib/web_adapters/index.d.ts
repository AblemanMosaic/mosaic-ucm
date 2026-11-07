export interface MosaicAdapterOptions {
  endpoint: string;
  width?: number;
  height?: number;
  title?: string;
  tagName?: string;
}

export declare function createMosaicReactBinding(React: any, tagName?: string): (props: MosaicAdapterOptions) => any;
export declare function createMosaicVueBinding(Vue: any, tagName?: string): any;
export declare function mosaicUI(node: HTMLElement, options?: MosaicAdapterOptions): {
  update(options: MosaicAdapterOptions): void;
  destroy(): void;
};
