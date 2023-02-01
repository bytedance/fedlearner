import { DateTimeInfo } from 'typings/app';
import { ValueType } from 'typings/settings';

export interface FileQueryParams {
  path: string;
}
export interface FileTreeNode {
  filename: string;
  path: string;
  /** File size */
  size: number;
  /** Last Time Modified */
  mtime: number;
  is_directory: boolean;
  files: FileTreeNode[];
}

export enum EnumAlgorithmProjectType {
  UNSPECIFIED = 'UNSPECIFIED',
  TREE_VERTICAL = 'TREE_VERTICAL',
  TREE_HORIZONTAL = 'TREE_HORIZONTAL',
  NN_VERTICAL = 'NN_VERTICAL',
  NN_HORIZONTAL = 'NN_HORIZONTAL',
  TRUSTED_COMPUTING = 'TRUSTED_COMPUTING',
  NN_LOCAL = 'NN_LOCAL',
}

export enum EnumAlgorithmProjectSource {
  PRESET = 'PRESET',
  USER = 'USER',
  THIRD_PARTY = 'THIRD_PARTY',
}

export enum AlgorithmStatus {
  UNPUBLISHED = 'UNPUBLISHED',
  PUBLISHED = 'PUBLISHED',
}

export enum AlgorithmReleaseStatus {
  UNRELEASED = 'UNRELEASED',
  RELEASED = 'RELEASED',
}

export enum AlgorithmVersionStatus {
  UNPUBLISHED = 'UNPUBLISHED',
  PUBLISHED = 'PUBLISHED',
  PENDING = 'PENDING',
  DECLINED = 'DECLINED',
  APPROVED = 'APPROVED',
}

export type AlgorithmParameter = {
  name: string;
  value: string;
  required: boolean;
  display_name: string;
  comment: string;
  value_type: ValueType;
};

export type AlgorithmProject = {
  id: ID;
  name: string;
  project_id: ID;
  type: EnumAlgorithmProjectType;
  source?: EnumAlgorithmProjectSource | `${EnumAlgorithmProjectSource}`;
  creator_id: ID | null;
  username: string;
  participant_id: ID | null;
  participant_name?: string;
  path: string;
  publish_status: AlgorithmStatus | `${AlgorithmStatus}`;
  release_status: AlgorithmReleaseStatus | `${AlgorithmReleaseStatus}`;
  algorithms?: Algorithm[];
  parameter: {
    variables: AlgorithmParameter[];
  } | null;
  favorite?: boolean;
  comment: string | null;
  latest_version: number;
  uuid?: ID;
} & DateTimeInfo;

export type Algorithm = Omit<
  AlgorithmProject,
  'publish_status' | 'release_status' | 'latest_version'
> & {
  version: number;
  algorithm_project_id: ID;
  algorithm_project_uuid?: ID;
  status: AlgorithmVersionStatus;
  uuid?: ID;
  participant_id?: ID | null;
};

export interface UploadFileQueryParams {
  /** Parent path */
  path: string;
  /** File name */
  filename: string;
  /** File */
  file: File;
}
export interface UpdateFileQueryParams {
  /** Parent path */
  path: string;
  /** File name */
  filename: string;
  is_directory: boolean;
  /** File Content */
  file?: string;
}
export interface RenameFileQueryParams {
  /** Old full file Path */
  path: string;
  /** New full file path */
  dest: string;
}
export interface DeleteFileQueryParams {
  /** Full File path */
  path: string;
}

export interface FileContent {
  path: string;
  filename: string;
  content: string;
}
export enum OperationType {
  ADD = 'ADD',
  EDIT = 'EDIT',
  DELETE = 'DELETE',
  RENAME = 'RENAME',
}

export interface OperationRecord {
  type: `${OperationType}`;
  path: string;
  isFolder: boolean;
  content?: string;
  newPath?: string;
}
export interface AlgorithmProjectQuery {
  keyword?: string;
  type?: string;
  sources?: string;
}
