import React from 'react';
import {Composition} from 'remotion';
import {Overlay, type OverlayProps} from './Overlay';

const defaults: OverlayProps = {
  fps: 30,
  durationInFrames: 1986,
  width: 720,
  height: 1280,
  gold: 'rgb(226,178,38)',
  goldLight: 'rgb(245,210,96)',
  segments: [],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Overlay"
    component={Overlay}
    durationInFrames={1986}
    fps={30}
    width={720}
    height={1280}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({
      durationInFrames: Math.max(1, Math.ceil(props.durationInFrames)),
      fps: props.fps,
      width: props.width,
      height: props.height,
    })}
  />
);
