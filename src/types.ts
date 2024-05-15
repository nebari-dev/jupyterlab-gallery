export interface IExhibitReply {
  exhibits: IExhibit[];
  apiVersion: string;
}

export interface IExhibit {
  // from configuration file
  repository: string;
  title: string;
  description: string;
  icon: string;
  // state from server
  localPath: boolean;
  revision: string;
  lastUpdated: string;
  updatesAvailable: boolean;
}
