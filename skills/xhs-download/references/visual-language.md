# Product visual language

Use two themes only:

1. Default `neo`: low-saturation cool gray-blue background, same-family surfaces, soft bidirectional shadows, dark gray-blue primary action.
2. Optional `glass`: restrained light blue-gray transparency, readable solid surfaces, thin borders, light blur, no neon purple-blue.

Persist theme, output directory, and mode in local storage. Keep one visually dominant primary button. Prioritize readable Chinese, real operations, keyboard focus, disabled/loading states, and 160–240 ms state transitions. Support `prefers-reduced-motion` and an opaque fallback when backdrop blur is unavailable.

The same two-theme contract applies to Web, Windows desktop, and Android. A platform release is incomplete if it silently drops theme switching, uses a differently named palette, or resets the selected theme. Dialogs inherit the active palette.

Windows UI changes must be checked at 100%, 125%, 150%, and 175% display scaling, including 1280×720. The settings save button and all bottom actions must remain visible; use scrolling or resizable/minimum-size layouts instead of a small fixed dialog. Android must be checked on a real device with vertical scrolling and enlarged system text.

Do not use pure-white card walls, generic admin-dashboard statistics, large saturated-blue containers, decorative fake controls, or theme changes that reset after refresh.

The canonical full specification is stored in the user's shared memory at:

`D:\AICode\AI\data\01-团建策划-江湖有旅人\05-知识库\07-销售转化与策划师承接系统\06-转化助手应用\说明\视觉语言规范.md`
