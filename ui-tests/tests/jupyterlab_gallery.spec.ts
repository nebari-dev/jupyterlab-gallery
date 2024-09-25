import { expect, test } from '@jupyterlab/galata';
import { Page } from '@playwright/test';
import type {
  IGalleryReply,
  IExhibitReply,
  IExhibit
} from 'jupyterlab-gallery';

interface IServerSideExhibit {
  git: string;
  homepage?: string;
  title: string;
  description?: string;
  icon?: string;
  branch?: string;
  depth?: number;
}

const niceExhibitConfigs: IServerSideExhibit[] = [
  {
    git: 'https://github.com/numba/nvidia-cuda-tutorial.git',
    homepage: 'https://github.com/numba/nvidia-cuda-tutorial',
    title: 'Numba for CUDA',
    description: 'Nvidia contributed CUDA tutorial for Numba'
  },
  {
    git: 'https://github.com/yunjey/pytorch-tutorial.git',
    homepage: 'https://github.com/yunjey/pytorch-tutorial',
    title: 'PyTorch Tutorial',
    description: 'PyTorch Tutorial for Deep Learning Researchers',
    icon: 'https://github.com/yunjey/pytorch-tutorial/raw/master/logo/pytorch_logo_2018.svg'
  },
  {
    git: 'https://github.com/jupyter-widgets/tutorial.git',
    homepage: 'https://github.com/jupyter-widgets/tutorial',
    title: 'Jupyter Widgets Tutorial',
    description: 'The Jupyter Widget Ecosystem'
  },
  {
    git: 'https://github.com/amueller/scipy-2018-sklearn.git',
    homepage: 'https://github.com/amueller/scipy-2018-sklearn',
    title: 'Scikit-learn Tutorial 2018',
    description: 'SciPy 2018 Scikit-learn Tutorial'
  },
  {
    git: 'https://github.com/nebari-dev/nebari.git',
    homepage: 'https://github.com/nebari-dev/nebari',
    title: 'Nebari',
    description: 'Nebari - your open source data science platform',
    icon: 'https://raw.githubusercontent.com/nebari-dev/nebari-design/main/logo-mark/horizontal/Nebari-Logo-Horizontal-Lockup.svg'
  },
  {
    git: 'https://github.com/jupyterlab/jupyterlab.git',
    homepage: 'https://github.com/jupyterlab/jupyterlab/',
    title: 'JupyterLab',
    description:
      'JupyterLab is a highly extensible, feature-rich notebook authoring application and editing environment, and is a part of Project Jupyter',
    icon: 'https://raw.githubusercontent.com/jupyterlab/jupyterlab/main/packages/ui-components/style/icons/jupyter/jupyter.svg'
  }
];

const edgeCaseExhibitConfigs: IServerSideExhibit[] = [
  {
    git: 'https://github.com/krassowski/example-private-repository.git',
    homepage: 'https://github.com/krassowski/example-private-repository/',
    title: 'Private repository'
  },
  {
    git: 'https://github.com/jupyter-widgets/tutorial.git',
    title: 'Example without description'
  },
  {
    git: 'https://gitlab.gnome.org/GNOME/atomix.git',
    title: 'GNOME atomix',
    description: 'Example without icon'
  },
  {
    git: 'https://github.com/nebari-dev/nebari.git',
    homepage: 'https://github.com/nebari-dev/nebari',
    title: 'Empty icon',
    description: 'Empty icon should show social card for GitHub repos',
    icon: ''
  }
];
function mockExhibit(config: IServerSideExhibit, id: number): IExhibit {
  const git_url = config.git.split('/');
  const repo_name = git_url.pop()!.split('.')[0];
  const repo_owner = git_url.pop();

  return {
    homepage: config.homepage,
    title: config.title,
    description: config.description,
    icon:
      config.icon ??
      `https://opengraph.githubassets.com/1/${repo_owner}/${repo_name}`,
    id,
    isCloned: false,
    localPath: 'clone/path/' + repo_name,
    revision: 'revision-id'
  };
}

const niceExhibits: IExhibit[] = niceExhibitConfigs.map((config, index) => {
  return mockExhibit(config, index);
});

const edgeCaseExhibits: IExhibit[] = edgeCaseExhibitConfigs.map(
  (config, index) => {
    return mockExhibit(config, index);
  }
);

const defaultGalleryReplies: IGalleryReply = {
  title: 'Gallery',
  exhibitsConfigured: true,
  hideGalleryWithoutExhibits: false,
  apiVersion: '1.0'
};

const defaultExhibitsReply: IExhibitReply = {
  exhibits: niceExhibits
};

async function mockGalleryEndpoint(
  page: Page,
  gallery: Partial<IGalleryReply> = {}
): Promise<void> {
  await page.route(/\/jupyterlab-gallery\/gallery/, (route, request) => {
    switch (request.method()) {
      case 'GET':
        return route.fulfill({
          status: 200,
          body: JSON.stringify({
            ...defaultGalleryReplies,
            ...gallery
          })
        });
      default:
        return route.continue();
    }
  });
}

async function mockExhibitsEndpoint(
  page: Page,
  exhibits: Partial<IExhibitReply> = {}
): Promise<void> {
  await page.route(/\/jupyterlab-gallery\/exhibits/, (route, request) => {
    switch (request.method()) {
      case 'GET':
        return route.fulfill({
          status: 200,
          body: JSON.stringify({
            ...defaultExhibitsReply,
            ...exhibits
          })
        });
      default:
        return route.continue();
    }
  });
}

test.describe('Integration with jupyterlab-launchpad', () => {
  /**
   * Don't load JupyterLab webpage before running the tests.
   */
  test.use({ autoGoto: false });

  const EXAMPLE_CARD = 1;

  test('Launchpad integration', async ({ page }) => {
    await mockGalleryEndpoint(page);
    await mockExhibitsEndpoint(page);

    await page.goto();

    // collapse the "create empty" section
    await page.locator('.jp-Launcher-openByType summary').click();
    // wait for animations to complete
    await page.waitForTimeout(400);

    const launcher = page.locator('.jp-LauncherBody');

    const mainMenu = page.locator('#jp-MainMenu');

    // move the mouse away from the summary button
    await mainMenu.hover();
    await page.waitForTimeout(100);

    expect(await launcher.screenshot()).toMatchSnapshot('in-launchpad.png');
  });

  test('On hover - fresh', async ({ page }) => {
    await mockGalleryEndpoint(page);
    await mockExhibitsEndpoint(page, {
      exhibits: [niceExhibits[EXAMPLE_CARD]]
    });

    await page.goto();

    const card = page.locator('.jp-Exhibit').first();
    await card.hover();
    expect(await card.screenshot()).toMatchSnapshot('on-hover-fresh.png');
  });

  test('On hover - cloned', async ({ page }) => {
    await mockGalleryEndpoint(page);
    await mockExhibitsEndpoint(page, {
      exhibits: [{ ...niceExhibits[EXAMPLE_CARD], isCloned: true }]
    });

    await page.goto();

    const card = page.locator('.jp-Exhibit').first();
    await card.hover();
    expect(await card.screenshot()).toMatchSnapshot('on-hover-cloned.png');
  });

  test('On hover - updates pending', async ({ page }) => {
    await mockGalleryEndpoint(page);
    await mockExhibitsEndpoint(page, {
      exhibits: [
        {
          ...niceExhibits[EXAMPLE_CARD],
          isCloned: true,
          updatesAvailable: true
        }
      ]
    });

    await page.goto();

    const card = page.locator('.jp-Exhibit').first();
    await card.hover();
    expect(await card.screenshot()).toMatchSnapshot(
      'on-hover-updates-pending.png'
    );
  });

  test('Odd cases', async ({ page }) => {
    await mockGalleryEndpoint(page, { title: 'Edge cases' });
    await mockExhibitsEndpoint(page, { exhibits: edgeCaseExhibits });
    await page.goto();
    // wait for pictures to settle
    await page.waitForTimeout(400);
    const gallery = page.locator('.jp-Gallery');
    expect(await gallery.screenshot()).toMatchSnapshot('odd-cases.png');
  });
});
