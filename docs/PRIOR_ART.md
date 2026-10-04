# Problem and differences

Research checked 2026-10-04. These are product/workflow references, not an exhaustive patent search.

- [obs-setup](https://github.com/stefanmunz/obs-setup) documents a real meetup setup, hardware-specific bindings, whole-collection overwrite, and absence of per-scene version control
- [Enterprise-deployment report](https://obsproject.com/forum/threads/obs-for-enterprise-wide-deployment.143997/post-527336) describes conferences, more than 30 scenes, manual versions/QA, and roughly 100 trained colleagues. This is historical evidence from 2021
- [Source Copy 0.3.0](https://obsproject.com/forum/resources/source-copy.1261/) already copies scenes, sources and filters. Its [pinned implementation](https://raw.githubusercontent.com/exeldro/obs-source-copy/0.3.0/source-copy.cpp) resolves existing sources by name. It does not perform baseline-aware three-way reconciliation
- [Scene Collection Manager](https://obsproject.com/forum/resources/scene-collection-manager.1434/) backs up/restores collections
- [Marketplace Connect](https://www.elgato.com/us/en/s/marketplace-connect-for-obs) installs collections and individual scenes

SceneReconcile's narrow difference is reconciling operator scene layout and incoming shared-source edits against a common native baseline, making conflicts and transitive impact visible, and carrying a new scene's dependencies. It is configuration collaboration, not media processing.

## Pinned native references

- [OBS 32.2.2 release](https://github.com/obsproject/obs-studio/releases/tag/32.2.2)
- [Scene collection save and Duplicate behavior](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/frontend/widgets/OBSBasic_SceneCollections.cpp)
- [Native import behavior](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/frontend/importers/studio.cpp)
- [Scene item identity and relative transforms](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/libobs/obs-scene.c)
- [Official OBS WebSocket protocol](https://github.com/obsproject/obs-websocket/blob/5.6.3/docs/generated/protocol.md)
- [Pinned main-canvas identity](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/libobs/obs-canvas.c): a source canvas_uuid must point to the fixed main canvas in this one-canvas profile
- [Color source settings and bounds](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/plugins/image-source/color-source.c)
- [Linux FreeType text settings](https://raw.githubusercontent.com/obsproject/obs-studio/32.2.2/plugins/text-freetype2/text-freetype2.c)
