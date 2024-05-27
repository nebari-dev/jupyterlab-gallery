import * as React from 'react';
import { ReactWidget, showErrorMessage } from '@jupyterlab/apputils';
import { Button, UseSignal } from '@jupyterlab/ui-components';
import { Contents } from '@jupyterlab/services';
import { IStream, Stream, Signal } from '@lumino/signaling';
import { TranslationBundle } from '@jupyterlab/translation';
import { IExhibit } from './types';
import { IExhibitReply } from './types';
import { requestAPI, eventStream, IStreamMessage } from './handler';

interface IActions {
  download(exhibit: IExhibit): Promise<void>;
  open(exhibit: IExhibit): Promise<void>;
}

export class GalleryWidget extends ReactWidget {
  constructor(options: {
    trans: TranslationBundle;
    openPath: (path: string) => void;
    fileChanged: Contents.IManager['fileChanged'];
    refreshFileBrowser: () => Promise<void>;
  }) {
    const { trans, fileChanged } = options;
    super();
    this._status = trans.__('Gallery loading...');
    this._actions = {
      open: async (exhibit: IExhibit) => {
        options.openPath(exhibit.localPath);
        // TODO: should it open the directory in the file browser?
        // should it also open a readme for this repository?
      },
      download: async (exhibit: IExhibit) => {
        const done = new Promise<void>((resolve, reject) => {
          this._stream.connect((_, e) => {
            if (e.exhibit_id === exhibit.id) {
              if (e.phase === 'finished') {
                resolve();
              } else if (e.phase === 'error') {
                reject();
              }
            }
          });
        });
        await requestAPI('pull', {
          method: 'POST',
          body: JSON.stringify({ exhibit_id: exhibit.id })
        });
        await done;
        await this._load();
        await options.refreshFileBrowser();
      }
    };
    // if user deletes a directory, reload the state
    fileChanged.connect((_, args) => {
      if (args.type === 'delete') {
        this._load();
      }
    });
    this._eventSource = eventStream(
      'pull',
      message => {
        this._stream.emit(message);
      },
      error => {
        // TODO
        console.error(error);
      }
    );
    void this._load();
  }

  dispose() {
    super.dispose();
    this._eventSource.close();
  }

  private _eventSource: EventSource;

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
    this.update();
  }

  get exhibits(): IExhibit[] | null {
    return this._exhibits;
  }

  set exhibits(value: IExhibit[] | null) {
    this._exhibits = value;
  }

  update() {
    super.update();
    this._update.emit();
  }

  render(): JSX.Element {
    return (
      <UseSignal signal={this._update}>
        {() => {
          if (this.exhibits) {
            return (
              <Gallery
                exhibits={this.exhibits}
                actions={this._actions}
                progressStream={this._stream}
              />
            );
          }
          return (
            <div className="jp-Gallery jp-mod-loading">{this._status}</div>
          );
        }}
      </UseSignal>
    );
  }
  private _update = new Signal<GalleryWidget, void>(this);
  private _exhibits: IExhibit[] | null = null;
  private _status: string;
  private _actions: IActions;
  private _stream: Stream<GalleryWidget, IStreamMessage> = new Stream(this);
}

function Gallery(props: {
  exhibits: IExhibit[];
  actions: IActions;
  progressStream: IStream<GalleryWidget, IStreamMessage>;
}): JSX.Element {
  return (
    <div className="jp-Gallery">
      {props.exhibits.map(exhibit => (
        <Exhibit
          key={exhibit.repository}
          exhibit={exhibit}
          actions={props.actions}
          progressStream={props.progressStream}
        />
      ))}
    </div>
  );
}

function Exhibit(props: {
  exhibit: IExhibit;
  actions: IActions;
  progressStream: IStream<GalleryWidget, IStreamMessage>;
}): JSX.Element {
  const { exhibit, actions } = props;
  const [progressMessage, setProgressMessage] = React.useState<string>();

  React.useEffect(() => {
    const listenToStreams = (_: GalleryWidget, message: IStreamMessage) => {
      const exhibitId = message.exhibit_id;
      if (exhibitId !== exhibit.id) {
        return;
      }
      if (message.phase === 'error') {
        showErrorMessage(
          'Could not download',
          message.output ?? 'Unknown error'
        );
      } else {
        const { output, phase } = message;
        setProgressMessage(output ? phase + ': ' + output : phase);
      }
    };
    props.progressStream.connect(listenToStreams);
    return () => {
      props.progressStream.disconnect(listenToStreams);
    };
  });
  return (
    <div className="jp-Exhibit">
      <h4 className="jp-Exhibit-title">{exhibit.title}</h4>
      <img src={exhibit.icon} className="jp-Exhibit-icon" alt={exhibit.title} />
      <div className="jp-Exhibit-description">{exhibit.description}</div>
      {progressMessage}
      <div className="jp-Exhibit-buttons">
        {!exhibit.isCloned ? (
          <Button
            onClick={async () => {
              setProgressMessage('Downloading');
              await actions.download(exhibit);
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
        {exhibit.isCloned && exhibit.updatesAvailable ? (
          <Button>Update</Button>
        ) : null}
      </div>
    </div>
  );
}
