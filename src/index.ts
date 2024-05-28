import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ITranslator, nullTranslator } from '@jupyterlab/translation';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import { IFileBrowserCommands } from '@jupyterlab/filebrowser';

import { ILauncher } from '@jupyterlab/launcher';
import type { INewLauncher } from 'jupyterlab-new-launcher/lib/types';

import { GalleryWidget } from './gallery';
import { galleryIcon } from './icons';
import { IGalleryReply } from './types';
import { requestAPI } from './handler';

function isNewLauncher(launcher: ILauncher): launcher is INewLauncher {
  return 'addSection' in launcher;
}

/**
 * Initialization data for the jupyterlab-gallery extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-gallery:plugin',
  description:
    'A JupyterLab gallery extension for presenting and downloading examples from remote repositories',
  autoStart: true,
  requires: [ISettingRegistry],
  optional: [IFileBrowserCommands, ITranslator, ILauncher],
  activate: async (
    app: JupyterFrontEnd,
    settingRegistry: ISettingRegistry,
    fileBrowserCommands: IFileBrowserCommands | null,
    translator: ITranslator | null,
    launcher: ILauncher | null
  ) => {
    console.log('JupyterLab extension jupyterlab-gallery is activated!');

    translator = translator ?? nullTranslator;
    const trans = translator.load('jupyterlab-gallery');
    const widget = new GalleryWidget({
      trans,
      openPath: (path: string) => {
        if (!fileBrowserCommands) {
          // TODO: Notebook v7 support
          throw Error('filebrowser not available');
        }
        app.commands.execute(fileBrowserCommands.openPath, { path });
      },
      fileChanged: app.serviceManager.contents.fileChanged,
      refreshFileBrowser: () => {
        return app.commands.execute('filebrowser:refresh');
      }
    });

    const data = await requestAPI<IGalleryReply>('gallery');
    const expectedVersion = '1.0';
    if (data.apiVersion !== expectedVersion) {
      console.warn(
        `jupyter-gallery API version out of sync, expected ${expectedVersion}, got ${data.apiVersion}`
      );
    }

    const title = data.title === 'Gallery' ? trans.__('Gallery') : data.title;
    // add the widget to sidebar before waiting for server reply to reduce UI jitter
    if (launcher && isNewLauncher(launcher)) {
      launcher.addSection({
        title,
        className: 'jp-Launcher-openExample',
        icon: galleryIcon,
        id: 'gallery',
        rank: 2.5,
        render: () => {
          return widget.render();
        }
      });
    } else {
      // fallback to placing it in the sidebar if new launcher is not installed
      widget.id = 'jupyterlab-gallery:sidebar';
      widget.title.icon = galleryIcon;
      widget.title.caption = title;
      widget.show();
      app.shell.add(widget, 'left', { rank: 850 });
    }

    try {
      const settings = await settingRegistry.load(plugin.id);
      console.log('jupyterlab-gallery settings loaded:', settings.composite);
    } catch (reason) {
      console.error('Failed to load settings for jupyterlab-gallery.', reason);
      return;
    }
  }
};

export default plugin;
