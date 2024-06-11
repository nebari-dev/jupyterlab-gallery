import * as React from 'react';
import { ReactWidget, showErrorMessage } from '@jupyterlab/apputils';
import {
  Button,
  UseSignal,
  folderIcon,
  downloadIcon,
  refreshIcon
} from '@jupyterlab/ui-components';
import { Contents } from '@jupyterlab/services';
import { IStream, Stream, Signal } from '@lumino/signaling';
import { TranslationBundle } from '@jupyterlab/translation';
import { IExhibit } from './types';
import { IExhibitReply } from './types';
import { requestAPI, eventStream, IStreamMessage, IProgress } from './handler';

interface IActions {
  download(exhibit: IExhibit): Promise<void>;
  open(exhibit: IExhibit): Promise<void>;
}

export class GalleryWidget extends ReactWidget {
  constructor(
    protected options: {
      trans: TranslationBundle;
      openPath: (path: string) => void;
      fileChanged: Contents.IManager['fileChanged'];
      refreshFileBrowser: () => Promise<void>;
    }
  ) {
    super();
    const { trans, fileChanged } = options;
    this._trans = trans;
    this._status = trans.__('Gallery loading...');
    this._actions = {
      open: async (exhibit: IExhibit) => {
        options.openPath(exhibit.localPath);
        // TODO: should it open the directory in the file browser?
        // should it also open a readme for this repository?
      },
      download: async (exhibit: IExhibit) => {
        const done = new Promise<void>((resolve, reject) => {
          const promiseResolver = (_: GalleryWidget, e: IStreamMessage) => {
            if (e.exhibit_id === exhibit.id) {
              if (e.phase === 'finished') {
                resolve();
                this._stream.disconnect(promiseResolver);
              } else if (e.phase === 'error') {
                reject();
                this._stream.disconnect(promiseResolver);
              }
            }
          };
          this._stream.connect(promiseResolver);
        });
        await requestAPI('pull', {
          method: 'POST',
          body: JSON.stringify({ exhibit_id: exhibit.id })
        });
        await done;
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
    this._stream.connect(this._reloadOnFinish);
    void this._load();
  }

  dispose() {
    super.dispose();
    this._eventSource.close();
    this._stream.disconnect(this._reloadOnFinish);
  }

  private _reloadOnFinish = async (_: GalleryWidget, e: IStreamMessage) => {
    if (e.phase === 'finished') {
      await this._load();
      await this.options.refreshFileBrowser();
    }
  };

  private _eventSource: EventSource;

  private async _load() {
    try {
      const data = await requestAPI<IExhibitReply>('exhibits');
      this.exhibits = data.exhibits;
      const allStatusesKnown = this.exhibits.every(
        exhibit =>
          !exhibit.isCloned || typeof exhibit.updatesAvailable === 'boolean'
      );
      if (!allStatusesKnown) {
        setTimeout(() => this._load(), 1000);
      }
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
                trans={this._trans}
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
  private _trans: TranslationBundle;
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
  trans: TranslationBundle;
}): JSX.Element {
  return (
    <div className="jp-Gallery">
      {props.exhibits.map(exhibit => (
        <Exhibit
          trans={props.trans}
          key={exhibit.repository}
          exhibit={exhibit}
          actions={props.actions}
          progressStream={props.progressStream}
        />
      ))}
    </div>
  );
}

interface IProgressState extends IProgress {
  state?: 'error';
}

function Exhibit(props: {
  exhibit: IExhibit;
  actions: IActions;
  progressStream: IStream<GalleryWidget, IStreamMessage>;
  trans: TranslationBundle;
}): JSX.Element {
  const { exhibit, actions } = props;
  const [progress, setProgress] = React.useState<IProgressState | null>(null);
  const [progressMessage, setProgressMessage] = React.useState<string>('');

  React.useEffect(() => {
    const listenToStreams = (_: GalleryWidget, message: IStreamMessage) => {
      const exhibitId = message.exhibit_id;
      if (exhibitId !== exhibit.id) {
        return;
      }

      switch (message.phase) {
        case 'error':
          showErrorMessage(
            'Could not download',
            message.output ?? 'Unknown error'
          );
          break;
        case 'progress':
          setProgress(message.output);
          setProgressMessage(message.output.message);
          break;
        case 'finished':
          setProgress(null);
          break;
        default:
          console.warn('Unhandled message', message);
          break;
      }
    };
    props.progressStream.connect(listenToStreams);
    return () => {
      props.progressStream.disconnect(listenToStreams);
    };
  });
  const updateStatusKnown = typeof exhibit.updatesAvailable === 'boolean';
  return (
    <div className="jp-Exhibit">
      <h4 className="jp-Exhibit-title">{exhibit.title}</h4>
      <div className="jp-Exhibit-icon">
        <img src={exhibit.icon} alt={exhibit.title} />
      </div>
      <div className="jp-Exhibit-description">{exhibit.description}</div>
      {progress ? (
        <div
          className={
            'jp-Exhibit-progressbar' +
            (progress.state === 'error' ? ' jp-Exhibit-progressbar-error' : '')
          }
        >
          <div
            className="jp-Exhibit-progressbar-filler"
            style={{ width: progress.progress * 100 + '%' }}
          ></div>
          <div className="jp-Exhibit-progressMessage">{progressMessage}</div>
        </div>
      ) : null}
      <div className="jp-Exhibit-buttons">
        {!exhibit.isCloned ? (
          <Button
            title={props.trans.__('Set up')}
            onClick={async () => {
              setProgressMessage('Downloading');
              setProgress({
                progress: 0.0,
                message: 'Initializing'
              });
              try {
                await actions.download(exhibit);
              } catch {
                setProgress({
                  ...(progress as any),
                  state: 'error'
                });
                setProgressMessage('');
              }
            }}
          >
            <downloadIcon.react />
          </Button>
        ) : (
          <>
            <Button
              minimal={true}
              title={props.trans.__('Open')}
              onClick={() => {
                actions.open(exhibit);
              }}
            >
              <folderIcon.react />
            </Button>
            <Button
              disabled={!exhibit.updatesAvailable}
              minimal={true}
              title={
                updateStatusKnown
                  ? props.trans.__('Fetch latest changes')
                  : props.trans.__('Checking upstream status')
              }
              onClick={async () => {
                setProgressMessage('Refreshing');
                setProgress({
                  progress: 0.25,
                  message: 'Refreshing'
                });
                try {
                  await actions.download(exhibit);
                  setProgress(null);
                } catch {
                  setProgress({
                    ...(progress as any),
                    state: 'error'
                  });
                  setProgressMessage('');
                }
              }}
            >
              {updateStatusKnown ? (
                <downloadIcon.react />
              ) : (
                <refreshIcon.react className="jp-spinningIcon" />
              )}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
