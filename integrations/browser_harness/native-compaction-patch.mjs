import {readFileSync} from 'node:fs';
import {nativeCompactionPatch} from './native-compaction.mjs';
process.stdout.write(nativeCompactionPatch(readFileSync(0,'utf8')));
