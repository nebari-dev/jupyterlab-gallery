import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ITranslator, nullTranslator } from '@jupyterlab/translation';
import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { requestAPI } from './handler';
import { GalleryWidget } from './gallery';
import { galleryIcon } from './icons';
import { IExhibitReply } from './types';

/**
 * Initialization data for the jupyterlab-gallery extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-gallery:plugin',
  description:
    'A JupyterLab gallery extension for presenting and downloading examples from remote repositories',
  autoStart: true,
  requires: [ISettingRegistry],
  optional: [ITranslator],
  activate: async (
    app: JupyterFrontEnd,
    settingRegistry: ISettingRegistry,
    translator: ITranslator | null
  ) => {
    console.log('JupyterLab extension jupyterlab-gallery is activated!');

    translator = translator ?? nullTranslator;
    const trans = translator.load('jupyterlab-gallery');
    const widget = new GalleryWidget();

    // TODO: should we put it in the sidebar, or in the main area?
    // add the widget to sidebar before waiting for server reply to reduce UI jitter
    widget.id = 'jupyterlab-gallery:sidebar';
    widget.title.icon = galleryIcon;
    widget.title.caption = trans.__('Gallery');
    widget.show();
    app.shell.add(widget, 'left', { rank: 850 });

    try {
      const settings = await settingRegistry.load(plugin.id);
      console.log('jupyterlab-gallery settings loaded:', settings.composite);
    } catch (reason) {
      console.error('Failed to load settings for jupyterlab-gallery.', reason);
      return;
    }

    try {
      const data = await requestAPI<IExhibitReply>('exhibits');
      widget.exhibits = data;
    } catch (reason) {
      console.error(
        `The jupyterlab_gallery server extension appears to be missing.\n${reason}`
      );
    }
  }
};

export default plugin;
