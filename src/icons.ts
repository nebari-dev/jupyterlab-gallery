import { LabIcon } from '@jupyterlab/ui-components';
import gallerySvgstr from '../style/icons/md/gallery.svg';
import repositorySvgstr from '../style/icons/md/repository.svg';

export const galleryIcon = new LabIcon({
  name: 'jupyterlab-gallery:gallery',
  svgstr: gallerySvgstr
});

export const repositoryIcon = new LabIcon({
  name: 'jupyterlab-gallery:repository',
  svgstr: repositorySvgstr
});
