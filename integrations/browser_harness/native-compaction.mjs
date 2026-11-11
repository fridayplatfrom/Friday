// A conservative local planning budget, not a claim about a website's hidden
// context capacity. Harness uses it to schedule its own native compactor.
export const FRIDAY_CONTEXT_WINDOW = 32768;
export const FRIDAY_COMPACTION_POLICY = Object.freeze({
  provider:'browser-web', model:'chatgpt-web', thresholdRatio:0.6,
  headroomTokens:4096, retainTokens:2048, maxTokens:2048,
});

/** Preserve every current preset plugin while configuring its native compactor. */
export function nativeCompactionPatch(dump) {
  const blocks=[];
  for(const id of ['preset-standard','preset-ptc','preset-minimal','preset-cordis']) {
    const block=dump.match(new RegExp(`^- id: ${id}\\r?\\n[\\s\\S]*?(?=^- |$(?![\\s\\S]))`,'m'))?.[0];
    if(!block)continue;
    const pattern=/^([ \t]*)name: ['"]?@deepseek-ai\/dsh-compaction-basic['"]?[ \t]*\r?\n/m;
    const match=pattern.exec(block);if(!match)continue;
    const tail=block.slice(match.index+match[0].length);
    if(new RegExp(`^${match[1]}config:`).test(tail))throw new Error(`Preserve the existing custom compaction config in ${id}; update its browser-web model policy explicitly.`);
    const indent=match[1];const policy=Object.entries(FRIDAY_COMPACTION_POLICY).map(([key,value])=>`${indent}      ${key}: ${value}`).join('\n');
    const addition=`${indent}config:\n${indent}  auto: true\n${indent}  modelPolicies:\n${indent}    - provider: browser-web\n${policy.split('\n').slice(1).join('\n')}\n`;
    blocks.push(block.slice(0,match.index)+match[0]+addition+tail);
  }
  if(!blocks.length)throw new Error('No native Harness compaction presets found; profile was not changed.');
  return '# BEGIN FRIDAY NATIVE COMPACTION\n'+blocks.join('\n')+'\n# END FRIDAY NATIVE COMPACTION\n';
}
