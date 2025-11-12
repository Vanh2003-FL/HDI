data = []
for (var phase of a.phases) {
    for (var wp of phase.workPackages) {
        for (var task of wp.tasks) {
            data.push([task.id, wp.id, wp.code])
        }
        for (var child of wp.children) {
            for (var c_task of child.tasks) {
                data.push([c_task.id, child.id, child.code])
            }
        }
    }
}
data


data = []
for (var phase of a) {
    for (var wp of phase.workPackages) {
        for (var task of wp.tasks) {
            data.push([task.id, wp.id, wp.code])
        }
        for (var child of wp.children) {
            for (var c_task of child.tasks) {
                data.push([c_task.id, child.id, child.code])
            }
        }
    }
}
data