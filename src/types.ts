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
  id: number;
  isCloned: boolean;
  localPath: string;
  revision: string;
  lastUpdated: string;
  updatesAvailable: boolean;
}
