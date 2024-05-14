import * as React from 'react';
import { ReactWidget } from '@jupyterlab/apputils';

export class GalleryWidget extends ReactWidget {
  render(): JSX.Element {
    return <Gallery />;
  }
}

function Gallery(): JSX.Element {
  return <div>Hello world</div>;
}
