import test from 'node:test';
import assert from 'node:assert/strict';
import {recentMetrics,failureDetails,recoveryDiagnostic} from '../diagnostics.mjs';

test('a page channel closing after acceptance is a connection failure with no safe automatic resend',()=>{
 const error='A listener indicated an asynchronous response by returning true, but the message channel closed before a response was received';
 const detail=recoveryDiagnostic(error,{site:'kimi-web',submitted:true});
 assert.equal(detail.category,'connection');assert.equal(detail.submission,'submitted');assert.equal(detail.canRetryWithoutDuplicateSubmission,false);assert.equal(detail.automaticResubmit,false);
 assert.match(detail.nextAction,/page listener disconnected/);
});

test('failure guidance separates browser policy, account, transport and reply-format errors',()=>{
 assert.equal(failureDetails('net::ERR_BLOCKED_BY_CLIENT').category,'browser-policy');
 assert.equal(failureDetails('Your account changed').category,'website-access');
 assert.equal(failureDetails('Invalid tool-request JSON; nothing executed.').category,'reply-format');
 assert.equal(failureDetails('Website request timed out').category,'connection');
 assert.equal(failureDetails('Request exceeds the transport limit').category,'context-pressure');
 assert.equal(failureDetails('Attachment transfer limit is 32 MB').category,'file-transfer');
 assert.ok(!JSON.stringify(failureDetails('SECRET_VALUE')).includes('SECRET_VALUE'));
});

test('observed Kimi capacity notice offers waiting or manual switching without inventing a cooldown or requiring purchase',()=>{
 const text='Too many people are chatting with Kimi; a subscription will grant you priority access.';
 const detail=failureDetails(text);assert.equal(detail.category,'website-capacity');
 assert.match(detail.nextAction,/Wait and retry/);assert.match(detail.nextAction,/select another model/);assert.match(detail.nextAction,/has not provided a retry time/);
 const recovery=recoveryDiagnostic(text,{site:'kimi-web',submitted:true});
 assert.equal(recovery.automaticResubmit,false);assert.equal(recovery.automaticProviderSwitch,false);
 assert.notEqual(failureDetails('Kimi request timed out').category,'website-capacity');
});
test('bounded metrics count attempts once and disclose no request content or identifiers',()=>{
 const event=(type,at,id='private-id')=>({type,at,data:{id,prompt:'SECRET_PROMPT',token:'SECRET_TOKEN'}});
 const events=[event('request',100),event('reply',130),event('complete',200),event('complete',210),event('failed',220),
 event('request',300,'second'),event('cancelled',350,'second'),event('waiting-image-job',400)];
 const result=recentMetrics(events);assert.equal(result.completed,1);assert.equal(result.failed,0);assert.equal(result.cancelled,1);
 assert.equal(result.meanDurationMs,75);assert.equal(result.meanFirstObservedReplyMs,30);assert.equal(result.imageWaits,1);
 assert.equal(recentMetrics(events,{limit:2}).attempts,0);
 assert.ok(!/SECRET|private-id/.test(JSON.stringify(result)));
});
