import * as React from 'react';
import { ReactWidget } from '@jupyterlab/apputils';
import { IExhibit } from './types';

export class GalleryWidget extends ReactWidget {
  // TODO make use of exhibits, show placeholder when not yet loaded
  get exhibits(): IExhibit[] | null {
    return this._exhibits;
  }

  set exhibits(value: IExhibit[] | null) {
    // TODO trigger lumino update message to refresh when set
    this._exhibits = value;
  }

  render(): JSX.Element {
    if (this.exhibits) {
      return <Gallery exhibits={this.exhibits} />;
    }
    // TODO: show server exception here if available
    return <div>Gallery loading...</div>;
  }
  private _exhibits: IExhibit[] | null = null;
}

function Gallery(props: { exhibits: IExhibit[] }): JSX.Element {
  return <div>Hello world</div>;
}
