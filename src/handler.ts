import { URLExt } from '@jupyterlab/coreutils';
import { fetchEventSource } from '@microsoft/fetch-event-source';

import { ServerConnection } from '@jupyterlab/services';

/**
 * Call the API extension
 *
 * @param endPoint API REST end point for the extension
 * @param init Initial values for the request
 * @returns The response body interpreted as JSON
 */
export async function requestAPI<T>(
  endPoint: string,
  namespace: string,
  init: RequestInit = {}
): Promise<T> {
  // Make request to Jupyter API
  const settings = ServerConnection.makeSettings();
  const requestUrl = URLExt.join(settings.baseUrl, namespace, endPoint);

  let response: Response;
  try {
    response = await ServerConnection.makeRequest(requestUrl, init, settings);
  } catch (error) {
    throw new ServerConnection.NetworkError(error as any);
  }

  let data: any = await response.text();

  if (data.length > 0) {
    try {
      data = JSON.parse(data);
    } catch (error) {
      console.log('Not a JSON response body.', response);
    }
  }

  if (!response.ok) {
    throw new ServerConnection.ResponseError(response, data.message || data);
  }

  return data;
}

export interface IProgress {
  progress: number;
  message: string;
}

export interface IProgressStreamMessage {
  output: IProgress;
  phase: 'progress';
  exhibit_id: number;
}

export interface ITextStreamMessage {
  output?: string;
  phase: 'error' | 'finished' | 'syncing';
  exhibit_id: number;
}

export type IStreamMessage = IProgressStreamMessage | ITextStreamMessage;

export interface IEventStream {
  close: () => void;
  promise: Promise<void>;
}

export function eventStream(
  endPoint = '',
  onStream: (message: IStreamMessage) => void,
  onError: (error: Event) => void,
  namespace: string
): IEventStream {
  const settings = ServerConnection.makeSettings();
  let requestUrl = URLExt.join(settings.baseUrl, namespace, endPoint);
  const xsrfTokenMatch = document.cookie.match('\\b_xsrf=([^;]*)\\b');
  if (xsrfTokenMatch) {
    const fullUrl = new URL(requestUrl);
    fullUrl.searchParams.append('_xsrf', xsrfTokenMatch[1]);
    requestUrl = fullUrl.toString();
  }
  const controller = new AbortController();
  const promise = fetchEventSource(requestUrl, {
    onmessage: event => {
      const data = JSON.parse(event.data);
      onStream(data);
    },
    onerror: error => {
      onError(error);
    },
    headers: {
      Authorization: `token ${settings.token}`
    },
    signal: controller.signal
  });
  const close = () => {
    controller.abort();
  };
  // https://bugzilla.mozilla.org/show_bug.cgi?id=833462
  window.addEventListener('beforeunload', () => {
    close();
  });
  return {
    close,
    promise
  };
}
