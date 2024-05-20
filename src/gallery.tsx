import * as React from 'react';
import { ReactWidget, showErrorMessage } from '@jupyterlab/apputils';
import { Button } from '@jupyterlab/ui-components';
import { TranslationBundle } from '@jupyterlab/translation';
import { IExhibit } from './types';
import { IExhibitReply } from './types';
import { requestAPI } from './handler';

interface IActions {
  download(exhibit: IExhibit): Promise<void>;
  open(exhibit: IExhibit): Promise<void>;
  //update(exhibit: IExhibit): Promise<void>
}

interface IDownloadReply {
  status: 'ok';
  error: string;
}

export class GalleryWidget extends ReactWidget {
  constructor(options: {
    trans: TranslationBundle;
    openPath: (path: string) => void;
  }) {
    const { trans } = options;
    super();
    this._status = trans.__('Gallery loading...');
    this._actions = {
      download: async (exhibit: IExhibit) => {
        const reply = await requestAPI<IDownloadReply>('download', {
          body: JSON.stringify({ exhibit }),
          method: 'POST'
        });
        if (reply.status !== 'ok') {
          showErrorMessage('Could not download', reply.error);
        }
      },
      open: async (exhibit: IExhibit) => {
        options.openPath(exhibit.localPath);
        // TODO: should it open the directory in the file browser?
        // should it also open a readme for this repository?
        //options.
      }
    };
    void this._load();
  }

  private async _load() {
    try {
      const data = await requestAPI<IExhibitReply>('exhibits');
      const expectedVersion = '1.0';
      if (data.apiVersion !== expectedVersion) {
        console.warn(
          `jupyter-gallery API version out of sync, expected ${expectedVersion}, got ${data.apiVersion}`
        );
      }
      this.exhibits = data.exhibits;
    } catch (reason) {
      this._status = `jupyterlab_gallery server failed:\n${reason}`;
    }
  }

  get exhibits(): IExhibit[] | null {
    return this._exhibits;
  }

  set exhibits(value: IExhibit[] | null) {
    this._exhibits = value;
    this.update();
  }

  render(): JSX.Element {
    if (this.exhibits) {
      return <Gallery exhibits={this.exhibits} actions={this._actions} />;
    }
    return <div className="jp-Gallery jp-mod-loading">{this._status}</div>;
  }
  private _exhibits: IExhibit[] | null = null;
  private _status: string;
  private _actions: IActions;
}

function Gallery(props: {
  exhibits: IExhibit[];
  actions: IActions;
}): JSX.Element {
  return (
    <div className="jp-Gallery">
      {props.exhibits.map(exhibit => (
        <Exhibit
          key={exhibit.repository}
          exhibit={exhibit}
          actions={props.actions}
        />
      ))}
    </div>
  );
}

function Exhibit(props: { exhibit: IExhibit; actions: IActions }): JSX.Element {
  const { exhibit, actions } = props;
  return (
    <div className="jp-Exhibit">
      <h4 className="jp-Exhibit-title">{exhibit.title}</h4>
      <img src={exhibit.icon} className="jp-Exhibit-icon" alt={exhibit.title} />
      <div className="jp-Exhibit-description">{exhibit.description}</div>
      <div className="jp-Exhibit-buttons">
        {!exhibit.isCloned ? (
          <Button
            onClick={() => {
              actions.download(exhibit);
            }}
          >
            Setup up
          </Button>
        ) : (
          <Button
            onClick={() => {
              actions.open(exhibit);
            }}
          >
            Open
          </Button>
        )}
        {exhibit.updatesAvailable ? <Button>Update</Button> : null}
      </div>
    </div>
  );
}
