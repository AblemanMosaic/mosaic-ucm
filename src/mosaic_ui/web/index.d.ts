export interface MosaicUIOptions {
  endpoint: string;
  width?: number;
  height?: number;
  title?: string;
  tagName?: string;
}

export declare class MosaicUIElement extends HTMLElement {
  endpointURL(): URL;
  refresh(): void;
}

export declare function defineMosaicUI(tagName?: string): string;
